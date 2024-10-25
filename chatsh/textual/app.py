#!/usr/bin/env python3

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, MarkdownViewer
from textual.containers import Horizontal
from rich.markdown import Markdown
from rich.console import Console

console = Console()
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, MarkdownViewer
from textual.containers import Vertical
from rich.markdown import Markdown

class ChatMessage:
    """A simple class to represent a chat message."""
    def __init__(self, sender: str, content: str, header_level: int = 2):
        self.sender = sender
        self.content = content
        self.header_level = header_level  # Markdown header level to simulate font size

    def to_markdown(self) -> str:
        """Convert the message to a Markdown string with appropriate styling."""
        if self.sender.lower() == "user":
            return f"**You:** {self.content}"
        else:
            # Use Markdown headers to simulate increasing font sizes
            header_prefix = "#" * self.header_level
            return f"{header_prefix} System: {self.content}"

class ChatApp(App):
    CSS_PATH = "chat_app.css"  # Optional: Define CSS for styling
    BINDINGS = [("ctrl+c", "quit", "Quit")]

    conversation: list[ChatMessage] = []
    system_reply_header_level: int = 2  # Starting header level for system replies

    def compose(self) -> ComposeResult:
        """Compose the UI components."""
        yield Header()
        yield Vertical(
            MarkdownViewer(id="chat_log"),  # Allow chat log to expand vertically
            Input(placeholder="Type your message here...", id="user_input"),
        )
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the conversation with random chat logs."""
        initial_messages = [
            ChatMessage("user", "Hello!"),
            ChatMessage("system", "Hi there!", self.system_reply_header_level),
            ChatMessage("user", "How are you?"),
            ChatMessage("system", "I'm a demo chat bot.", self.system_reply_header_level),
            ChatMessage("user", "Tell me something interesting."),
            ChatMessage("system", "Apples!", self.system_reply_header_level)
        ]

        for msg in initial_messages:
            self.conversation.append(msg)

        self.refresh_chat()

    async def on_input_submitted(self, message: Input.Submitted) -> None:
        """Handle user input submission."""
        user_text = message.value.strip()
        if user_text:
            # Add user's message
            user_message = ChatMessage("user", user_text)
            self.conversation.append(user_message)
            self.refresh_chat()

            # Clear the input box
            self.query_one("#user_input", Input).clear()

            # System's reply
            self.system_reply_header_level += 1  # Increase header level each reply (up to a max)
            if self.system_reply_header_level > 6:
                self.system_reply_header_level = 6  # Markdown supports up to ###### for headers

            system_message = ChatMessage("system", "Apples!", self.system_reply_header_level)
            self.conversation.append(system_message)
            self.refresh_chat()

    def refresh_chat(self) -> None:
        """Refresh the chat log display."""
        chat_log = self.query_one("#chat_log", MarkdownViewer)
        # Build the entire conversation as markdown
        chat_markdown = "\n\n".join([msg.to_markdown() for msg in self.conversation])
        # Update the MarkdownViewer with the new content
        chat_log.markdown = chat_markdown


if __name__ == "__main__":
    app = ChatApp()
    app.run()
