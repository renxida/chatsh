from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal, Container
from textual.widgets import RichLog, Static, Label
from textual.widget import Widget
from rich.console import RenderableType
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
from dataclasses import dataclass
from typing import Optional
from chatsh.conversation import ConversationHistory, ConversationEntry

class RoleLabel(Label):
    """A styled label for the chat role."""
    DEFAULT_CSS = """
    RoleLabel {
        width: 10;
        height: auto;
        padding: 1;
    }
    """
    
    def __init__(self, role: str):
        styles = {
            "user": "blue",
            "assistant": "green",
            "system": "red"
        }
        color = styles.get(role.lower(), "white")
        super().__init__(f"[{color}]{role.upper()}[/]")


class MessageContent(RichLog):
    """Widget for displaying message content with markdown."""
    DEFAULT_CSS = """
    MessageContent {
        width: 1fr;
        min-height: 1;
        height: auto;
        padding: 0 1;
    }
    """


class ChatMessage(Static):
    """A widget to display a single chat message with its role and content."""
    
    DEFAULT_CSS = """
    ChatMessage {
        layout: vertical;
        width: 100%;
        height: auto;
        margin: 0 0 1 0;
        background: $boost;
    }
    
    ChatMessage > Horizontal {
        height: auto;
        width: 100%;
        align: left middle;
        padding: 1;
    }
    
    ChatMessage > .execution-container {
        padding: 0 1 1 1;
        height: auto;
        width: 100%;
    }
    """

    def __init__(self, entry: ConversationEntry):
        super().__init__()
        self.entry = entry
        
    def compose(self) -> ComposeResult:
        with Horizontal():
            yield RoleLabel(self.entry.role)
            content = MessageContent()
            content.write(Markdown(self.entry.content))
            yield content
        
        if self.entry.execution_output:
            with Container(classes="execution-container"):
                # Use ConversationEntry's code block extraction
                commands = self.entry.extract_codeblocks()
                if commands:
                    yield Static(Panel(
                        Syntax("\n".join(commands), "bash", theme="monokai"),
                        title="Commands",
                        padding=(0, 1)
                    ))
                
                # Display execution output
                yield Static(Panel(
                    Syntax(self.entry.execution_output, "python", theme="monokai"),
                    title="Execution Output",
                    padding=(0, 1)
                ))


class ChatLog(Static):
    """Main widget to display the entire chat history."""
    
    DEFAULT_CSS = """
    ChatLog {
        layout: vertical;
        width: 100%;
        height: 100%;
        overflow-y: scroll;
        background: $surface;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.messages: list[ConversationEntry] = []
    
    def compose(self) -> ComposeResult:
        for entry in self.messages:
            yield ChatMessage(entry)
    
    async def add_message(self, entry: ConversationEntry) -> None:
        """Add a new message to the chat log."""
        self.messages.append(entry)
        message = ChatMessage(entry)
        await self.mount(message)
        message.scroll_visible()


class ChatApp(App):
    """Main application class."""
    
    CSS = """
    ChatApp {
        layout: vertical;
        background: $surface;
        height: 100%;
        width: 100%;
    }
    """
    
    BINDINGS = [("q", "quit", "Quit")]
    
    def __init__(self, conversation: ConversationHistory):
        super().__init__()
        self.chat_log = ChatLog()
        self.conversation = conversation
    
    def compose(self) -> ComposeResult:
        yield self.chat_log
    
    async def on_mount(self) -> None:
        """Load initial messages after the app is mounted."""
        for entry in self.conversation.entries:
            await self.chat_log.add_message(entry)
    
    async def add_message(self, entry: ConversationEntry) -> None:
        """Add a new message to the chat log."""
        await self.chat_log.add_message(entry)


def main():
    # Add some sample messages
    conversation = ConversationHistory()
    conversation.add_entry("user", "Hello! Can you help me with Python?")
    conversation.add_entry("assistant", """Sure! Here's a simple example:
```sh
python3 hello.py
```""", "Hello, World!")
    
    # Create and run the app with the conversation
    app = ChatApp(conversation)
    app.run()

if __name__ == "__main__":
    main()