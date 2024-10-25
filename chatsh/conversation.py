from dataclasses import dataclass
from typing import List, Optional, Tuple

import re
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax


@dataclass
class ConversationEntry:
    role: str
    content: str
    execution_output: Optional[str] = None

class ConversationHistory:
    def __init__(self):
        self.entries: List[ConversationEntry] = []

    def add_entry(self, role: str, content: str, execution_output: Optional[str] = None):
        self.entries.append(ConversationEntry(role, content, execution_output))


    def handle_back_command(self, user_message: str) -> List[ConversationEntry]:
        """
        Handle the back command from the user message.

        @return: list of removed entries. empty when not back command / nothing removed.
        """
        match = re.match(r'^(b|back)\s+(\d+)$', user_message.lower())
        if not match:
            if user_message.lower().strip() == 'b' or user_message.lower().strip() == 'back':
                return self.handle_back_command('back 1')
            else:
                return []

        back_pairs = int(match.group(2))
        
        removed_entries = self.back(back_pairs)
        return removed_entries

    def back(self, pairs: int) -> List[ConversationEntry]:
        assert self.entries[-1].role == 'assistant'
        messages = 2*pairs

        if messages <= 0 or messages > len(self.entries):
            return []
        removed = self.entries[-messages:]
        self.entries = self.entries[:-messages]
        return removed

    def get_chat_messages(self) -> List[dict]:
        return [
            {"role": entry.role, "content": entry.content}
            for entry in self.entries
            if entry.role in ['user', 'assistant']
        ]
    
    def construct_full_message(self, system_prompt: str) -> str:
        messages = []
        for entry in self.entries:
            if entry.role == 'user':
                messages.append(f"<USER>\n{entry.content}\n</USER>")
            elif entry.role == 'assistant':
                messages.append(f"<ASSISTANT>\n{entry.content}\n</ASSISTANT>")
            if entry.execution_output:
                messages.append(f"<SYSTEM>\n{entry.execution_output.strip()}\n</SYSTEM>")
        
        return f"{system_prompt}\n\n" + "\n".join(messages)
