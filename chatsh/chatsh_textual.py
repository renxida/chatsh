#!/usr/bin/env python3

import asyncio
from chatsh.chat import chat, MODELS

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, RichLog
from textual.containers import Container

class ChatSH(App):
    CSS = """
    #chat { width: 100%; height: 100%; }
    #input { dock: bottom; }
    """

    BINDINGS = [("ctrl+d", "quit", "Quit")]

    def __init__(self):
        super().__init__()
        self.chat_instance = chat(MODEL)
        self.last_output = ""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(RichLog(id="chat", wrap=True, markup=True))
        yield Input(id="input", placeholder="Type your message...")
        yield Footer()

    def on_mount(self):
        self.query_one("#chat").write(f"Welcome to ChatSH. Model: {MODELS.get(MODEL, MODEL)}\n")

    async def on_input_submitted(self, message: Input.Submitted):
        user_message = message.value
        self.query_one("#input").value = ""
        
        chat_log = self.query_one("#chat")
        chat_log.write(f"[bold blue]λ[/bold blue] {user_message}")

        if user_message.lower().startswith(("good bot", "bad bot")):
            chat_log.write("Conversation ended.")
            await asyncio.sleep(1)
            self.exit()
            return

        full_message = f"<SYSTEM>\n{self.last_output.strip()}\n</SYSTEM>\n<USER>\n{user_message}\n</USER>\n"
        
        async for chunk in self.chat_instance.ask(full_message, system=SYSTEM_PROMPT, model=MODEL, max_tokens=8192, system_cacheable=True, stream=True):
            chat_log.write(chunk, expand=True)

def main():
    app = ChatSH()
    app.run()

if __name__ == "__main__":
    main()
