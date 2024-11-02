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
from typing import Tuple, List, Optional
from chatsh.interaction_log import InteractionLog, InteractionType


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

async def process_assistant_response(chat_instance, full_message: str, system_prompt: str, model: str) -> str:
    assistant_message = ""
    with Live(console=console, refresh_per_second=4) as live:
        async for chunk in chat_instance.ask(full_message, system=system_prompt, model=model, max_tokens=8192, system_cacheable=True, stream=True):
            assistant_message += chunk
            live.update(Markdown(assistant_message))
    console.print()
    return assistant_message
    
async def handle_code_execution(codes: List[str], interaction_log: InteractionLog, parent_id: int) -> str:
    if codes:
        combined_code = '\n'.join(codes)
        console.print(Panel(Syntax(combined_code, "sh", theme="monokai", line_numbers=True)))
        
        prompt_id = await interaction_log.record_code_execution_prompt(combined_code, parent_id)
        
        if Confirm.ask("Execute the code?", default=True):
            await interaction_log.record_code_execution_decision(True, prompt_id)
            output = await execute_code(combined_code)
            console.print()
            console.print(Panel(Syntax(output, "sh", theme="monokai")))
            await interaction_log.record_code_output(output, prompt_id)
            return output
        else:
            await interaction_log.record_code_execution_decision(False, prompt_id)
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

async def handle_exit(user_message: str, interaction_log: InteractionLog):
    if user_message.lower().startswith("good bot"):
        message = "Thank you for the compliment! See you next time."
        console.print(Markdown(message))
        await interaction_log.record_exit(f"good bot: {message}")
    elif user_message.lower().startswith("bad bot"):
        message = "I'm sorry to hear that. The conversation has ended."
        console.print(Markdown(message))
        await interaction_log.record_exit(f"bad bot: {message}")
    else:
        message = "The conversation has ended with message: " + user_message + "."
        console.print(Markdown(message))
        await interaction_log.record_exit(f"conversation ended: {message}")
    
    log_file = interaction_log.current_file
    console.print(f"Conversation transcript saved to: {log_file}")
    subprocess.run(["gh", "gist", "edit", "d0976d9e693afaaca5befd6a0b52b698", "-a", str(log_file)])

from chatsh.conversation import ConversationHistory, ConversationEntry

async def main_loop(chat_instance, system_prompt: str, model: str):
    history = ConversationHistory()
    interaction_log = InteractionLog()
    prompt = UndeletablePrompt()
    
    # Record initial system setup
    await interaction_log.record_system_message(f"ChatSH Started with model: {MODELS.get(model, model)}")
    await interaction_log.record_system_message(system_prompt)

    while True:
        try:
            user_message = await prompt.get_input()
        except (EOFError, KeyboardInterrupt):
            await handle_exit("EOF", interaction_log)
            break

        if user_message.lower().startswith(("good bot", "bad bot")):
            await handle_exit(user_message, interaction_log)
            break

        removed_entries = history.handle_back_command(user_message)
        back_pairs = len(removed_entries) // 2
        if removed_entries:
            message = f"> Removed {back_pairs} most recent message pairs"
            console.print(Markdown(message))
            await interaction_log.record_back_command(back_pairs)
            
            console.print(Markdown("We are back at:"))
            last_entry = history.entries[-1] if history.entries else None
            if last_entry:
                console.print(Panel(Syntax(last_entry.content, "markdown", theme="monokai")))
            continue

        # Record user message
        user_msg_id = await interaction_log.record_user_message(user_message)
        history.add_entry('user', user_message)

        try:
            full_message = history.construct_full_message(system_prompt)
            assistant_message = await process_assistant_response(chat_instance, full_message, system_prompt, model)
            
            # Record assistant response
            assistant_msg_id = await interaction_log.record_llm_response(assistant_message, user_msg_id)
            history.add_entry('assistant', assistant_message)
            
            codes = history.entries[-1].get_codeblocks(last_only=True)
            if codes:
                execution_output = await handle_code_execution(codes, interaction_log, assistant_msg_id)
                history.entries[-1].execution_output = execution_output

        except Exception as error:
            error_str = str(error)
            console.print(f"[bold red]Error:[/bold red] {error_str}")
            await interaction_log.record_error(error_str, user_msg_id)


def main():
    model = setup_environment()
    system_prompt = load_system_prompt() + generate_system_description()
    chat_instance = chat(model)
    
    asyncio.run(main_loop(chat_instance, system_prompt, model))

if __name__ == "__main__":
    main()