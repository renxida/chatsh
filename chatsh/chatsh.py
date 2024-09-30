#!/usr/bin/env python3

import readline
import subprocess
import asyncio
import os
import sys
from datetime import datetime
import re
from chatsh.chat import chat, MODELS
from pathlib import Path
import shutil
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.panel import Panel
from rich.live import Live
from rich.prompt import Prompt, Confirm
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style

console = Console()
DEFAULT_MODEL = "s"
COMMAND_DESCRIPTIONS = {
    "rg": "faster replacement for grep",
    "fd": "faster alternative to find",
    "jq": "command-line JSON processor",
    "tldr": "simplified man pages",
    "ag": "code-searching tool similar to ack",
    "tmux": "terminal multiplexer",
}

def setup_environment():
    MODEL = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    print(f"Welcome to ChatSH. Model: {MODELS.get(MODEL, MODEL)}\n")
    return MODEL

def load_system_prompt():
    SYSTEM_PROMPT_FILE = Path(__file__).resolve().parent / 'system.prompt'
    with open(SYSTEM_PROMPT_FILE, "r") as f:
        return f.read()

async def get_shell_info():
    proc = await asyncio.create_subprocess_shell(
        'uname -v && $SHELL --version | head -n 1',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    return stdout.decode().strip()

def get_available_commands():
    return [f"{cmd}: {desc}" for cmd, desc in COMMAND_DESCRIPTIONS.items() if shutil.which(cmd)]

def generate_system_description():
    shell_info = asyncio.run(get_shell_info())
    available_commands = get_available_commands()
    return f"""
- system information:
{shell_info}

Available commands:
{os.linesep.join(available_commands)}
"""

def setup_history_file():
    xdg_data_home = os.getenv('XDG_DATA_HOME', Path(os.getenv('HOME')) / '.local' / 'share')
    HISTORY_DIR = Path(xdg_data_home) / 'chatsh_history'
    os.makedirs(HISTORY_DIR, exist_ok=True)
    return os.path.join(HISTORY_DIR, f"conversation_{datetime.now().isoformat().replace(':', '-')}.txt")

def append_to_history(conversation_file, role, message):
    formatted_message = f"<{role}>\n{message}\n</{role}>\n\n"
    with open(conversation_file, 'a') as f:
        f.write(formatted_message)

def extract_codes(text):
    regex = r"```sh([\s\S]*?)```"
    return [match.strip() for match in re.findall(regex, text)]

def handle_back_command(user_message, chat_instance):
    match = re.match(r'^(b|back)\s+(\d+)$', user_message.lower())
    if match:
        steps = int(match.group(2))
        removed_messages = chat_instance.back(steps)
        return True, steps
    return False, 0

async def execute_code(code):
    try:
        proc = await asyncio.create_subprocess_shell(
            code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        return f"{stdout.decode().strip()}{stderr.decode().strip()}"
    except Exception as error:
        return str(error)

async def process_assistant_response(chat_instance, full_message, system_prompt, model):
    assistant_message = ""
    with Live(console=console, refresh_per_second=4) as live:
        async for chunk in chat_instance.ask(full_message, system=system_prompt, model=model, max_tokens=8192, system_cacheable=True, stream=True):
            assistant_message += chunk
            live.update(Markdown(assistant_message))
    console.print()
    return assistant_message

async def handle_code_execution(codes):
    if codes:
        combined_code = '\n'.join(codes)
        console.print(Panel(Syntax(combined_code, "sh", theme="monokai", line_numbers=True)))
        
        if Confirm.ask("Execute the code?", default=True):
            output = await execute_code(combined_code)
            console.print()
            console.print(Panel(Syntax(output, "sh", theme="monokai")))
            return output
        else:
            console.print(Markdown('Execution skipped.'))
            return "Command skipped.\n"
    return ""


class UndeletablePrompt:
    def __init__(self):
        self.prompt_style = Style.from_dict({
            'lambda': '#00BFFF bold',  # Deep Sky Blue
            'separator': '#555555',    # Dim Gray
        })
        self.prompt_message = HTML('<lambda>λ</lambda> <separator> </separator> ')
        self.prompt_session = PromptSession(
            message=self.prompt_message,
            style=self.prompt_style
        )

    async def get_input(self):
        return await self.prompt_session.prompt_async()

async def main_loop(chat_instance, system_prompt, model, conversation_file):
    last_output = ""
    initial_user_message = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else None
    prompt = UndeletablePrompt()

    while True:
        if initial_user_message:
            user_message = initial_user_message
            initial_user_message = None
        else:
            user_message = await prompt.get_input()

        if user_message.lower().startswith(("good bot", "bad bot")):
            handle_exit(user_message, conversation_file)
            break

        is_back, steps = handle_back_command(user_message, chat_instance)
        if is_back:
            append_to_history(conversation_file, 'SYSTEM', f"<< Removed {steps} most recent message pairs >>")
            continue

        full_message = f"<SYSTEM>\n{last_output.strip()}\n</SYSTEM>\n<USER>\n{user_message}\n</USER>\n" if user_message.strip() else f"<SYSTEM>\n{last_output.strip()}\n</SYSTEM>"
        
        append_to_history(conversation_file, 'USER', user_message)

        try:
            assistant_message = await process_assistant_response(chat_instance, full_message, system_prompt, model)
            append_to_history(conversation_file, 'ChatSH', assistant_message)

            codes = extract_codes(assistant_message)
            last_output = await handle_code_execution(codes)
            append_to_history(conversation_file, 'SYSTEM', last_output)

        except Exception as error:
            console.print(f"[bold red]Error:[/bold red] {error}")
            append_to_history(conversation_file, 'ERROR', str(error))

def handle_exit(user_message, conversation_file):
    if user_message.lower().startswith("good bot"):
        console.print(Markdown("Thank you for the compliment! See you next time."))
        append_to_history(conversation_file, 'SYSTEM', "Thank you for the compliment! See you next time.")
    else:
        console.print(Markdown("I'm sorry to hear that. The conversation has ended."))
        append_to_history(conversation_file, 'SYSTEM', "I'm sorry to hear that. Please let me know how I can improve.")
    
    console.print(f"Conversation transcript saved to: {conversation_file}")
    subprocess.run(["gh", "gist", "edit", "d0976d9e693afaaca5befd6a0b52b698", "-a", conversation_file])

def main():
    model = setup_environment()
    system_prompt = load_system_prompt() + generate_system_description()
    conversation_file = setup_history_file()
    chat_instance = chat(model)
    
    asyncio.run(main_loop(chat_instance, system_prompt, model, conversation_file))

if __name__ == "__main__":
    main()
