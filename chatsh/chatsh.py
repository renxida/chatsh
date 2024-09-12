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
from rich.prompt import Confirm



console = Console()
# Default model if not specified
DEFAULT_MODEL = "s"
# Get model from command-line arguments or use default
MODEL = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL

print(f"Welcome to ChatSH. Model: {MODELS.get(MODEL, MODEL)}\n")

# System prompt to set the assistant's behavior
SYSTEM_PROMPT_FILE = Path(__file__).resolve().parent / 'system.prompt'
with open(SYSTEM_PROMPT_FILE, "r") as f:
    SYSTEM_PROMPT = f.read()

# Dictionary of commands and their descriptions
COMMAND_DESCRIPTIONS = {
    "rg": "faster replacement for grep",
    "fd": "faster alternative to find",
    "jq": "command-line JSON processor",
    "tldr": "simplified man pages",
    "ag": "code-searching tool similar to ack",
    "tmux": "terminal multiplexer",
}

async def get_shell():
    proc = await asyncio.create_subprocess_shell(
        'uname -v && $SHELL --version | head -n 1',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    return stdout.decode().strip()

def generate_system_description():
    result = f"""
- system information:
""" + asyncio.run(get_shell())

    available_commands = []
    for cmd, desc in COMMAND_DESCRIPTIONS.items():
        if shutil.which(cmd):
            available_commands.append(f"{cmd}: {desc}")

    result += "\n\n"
    result += "Available commands:\n" + "\n".join(available_commands)

    return result

SYSTEM_PROMPT += generate_system_description()

# Create a stateful chat instance
chat_instance = chat(MODEL)

# If there are words after the 'chatsh', set them as the initialUserMessage
initialUserMessage = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else None

# Get the XDG_DATA_HOME environment variable or default to ~/.local/share
xdg_data_home = os.getenv('XDG_DATA_HOME', Path(os.getenv('HOME')) / '.local' / 'share')
HISTORY_DIR = Path(xdg_data_home) / 'chatsh_history'

# Ensure the history directory exists
os.makedirs(HISTORY_DIR, exist_ok=True)

# Generate a unique filename for this conversation
conversationFile = os.path.join(HISTORY_DIR, f"conversation_{datetime.now().isoformat().replace(':', '-')}.txt")

# Function to append message to the conversation file
def append_to_history(role, message):
    formattedMessage = f"<{role}>\n{message}\n</{role}>\n\n"
    with open(conversationFile, 'a') as f:
        f.write(formattedMessage)

# Utility function to extract all code blocks from the assistant's message
def extract_codes(text):
    regex = r"```sh([\s\S]*?)```"
    return [match.strip() for match in re.findall(regex, text)]

def handle_back_command(user_message, chat_instance):
    match = re.match(r'^(b|back)\s+(\d+)$', user_message.lower())
    if match:
        steps = int(match.group(2))
        removed_messages = chat_instance.back(steps)
        append_to_history('SYSTEM', f"<< Removed {steps} most recent message pairs >>")
        return True
    return False

# Main interaction loop
async def main_loop():
    last_output = ""

    global initialUserMessage

    while True:
        if initialUserMessage:
            user_message = initialUserMessage
            initialUserMessage = None
        else:
            console.print("[bold blue]λ[/bold blue]", end=" ")
            user_message = input()

        if user_message.lower().startswith("good bot"):
            console.print(Markdown("Thank you for the compliment! See you next time."))
            append_to_history('USER', user_message)
            append_to_history('SYSTEM', "Thank you for the compliment! See you next time.")
            console.print(f"Conversation transcript saved to: {conversationFile}")
            subprocess.run(["gh", "gist", "edit", "d0976d9e693afaaca5befd6a0b52b698", "-a", conversationFile])
            break
        elif user_message.lower().startswith("bad bot"):
            console.print(Markdown("I'm sorry to hear that. The conversation has ended."))
            append_to_history('USER', user_message)
            append_to_history('SYSTEM', "I'm sorry to hear that. Please let me know how I can improve.")
            console.print(f"Conversation transcript saved to: {conversationFile}")
            subprocess.run(["gh", "gist", "edit", "d0976d9e693afaaca5befd6a0b52b698", "-a", conversationFile])
            break

        if handle_back_command(user_message, chat_instance):
            continue

        try:
            full_message = f"<SYSTEM>\n{last_output.strip()}\n</SYSTEM>\n<USER>\n{user_message}\n</USER>\n" if user_message.strip() else f"<SYSTEM>\n{last_output.strip()}\n</SYSTEM>"

            append_to_history('USER', user_message)

            # Stream the assistant's response
            assistant_message = ""
            with Live(console=console, refresh_per_second=4) as live:
                async for chunk in chat_instance.ask(full_message, system=SYSTEM_PROMPT, model=MODEL, max_tokens=8192, system_cacheable=True, stream=True):
                    assistant_message += chunk
                    live.update(Markdown(assistant_message))
            console.print()  # Add a newline after the response



            append_to_history('ChatSH', assistant_message)

            codes = extract_codes(assistant_message)
            last_output = ""

            if codes:
                combined_code = '\n'.join(codes)
                console.print(Panel(Syntax(combined_code, "sh", theme="monokai", line_numbers=True)))

                if Confirm.ask("Execute the code?", default=True):
                    try:
                        proc = await asyncio.create_subprocess_shell(
                            combined_code,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        stdout, stderr = await proc.communicate()
                        output = f"{stdout.decode().strip()}{stderr.decode().strip()}"
                        console.print()
                        console.print(Panel(Syntax(output, "sh", theme="monokai")))
                        last_output = output
                        append_to_history('SYSTEM', output)
                    except Exception as error:
                        output = str(error)
                        console.print(Panel(Syntax(output, "text", theme="monokai")))
                        last_output = output
                        append_to_history('SYSTEM', output)
                else:
                    console.print(Markdown('Execution skipped.'))
                    last_output = "Command skipped.\n"
                    append_to_history('SYSTEM', last_output)
                                      

        except Exception as error:
            console.print(f"[bold red]Error:[/bold red] {error}")
            append_to_history('ERROR', str(error))
def main():
    asyncio.run(main_loop())

if __name__ == "__main__":
    main()
