"""
Interaction log for storing and retrieving conversation interactions.

Eventually this would be used to inspect interaction histories, and hopefully enable features like:
- multiverse travel: examine different branches of the conversation and identify how to improve the model & the prompt
- conversation playback: replay the conversation from a specific point to understand the context
- training on the conversation branch that ended up being taken by the user to improve the model
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto, EnumMeta
from pathlib import Path
from dataclasses_json import dataclass_json, config
from typing import Optional, List, Dict, Any
import aiofiles
import json


class StrEnumMeta(EnumMeta):
    def __contains__(cls, item):
        if isinstance(item, str):
            try:
                cls(item)
            except ValueError:
                return False
            else:
                return True
        return super().__contains__(item)

class StrEnum(str, Enum, metaclass=StrEnumMeta):
    pass

class AutoNameLower(StrEnum):
    def _generate_next_value_(name, start, count, last_values):
        return name.lower()

class InteractionType(AutoNameLower):
    USER_MESSAGE = auto()
    LLM_RESPONSE = auto()
    CODE_EXECUTION_PROMPT = auto()
    CODE_EXECUTION_DECISION = auto()
    CODE_EXECUTION_OUTPUT = auto()
    BACK_COMMAND = auto()
    EXIT_COMMAND = auto()
    ERROR = auto()
    SYSTEM_MESSAGE = auto()


@dataclass_json
@dataclass
class Interaction:
    type: InteractionType
    content: str
    timestamp: datetime = field(
        metadata=config(
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat
        )
    )
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[int] = field(default=None)
    interaction_id: Optional[int] = field(default=None)


class InteractionLog:
    def __init__(self, log_dir: Optional[Path] = None):
        if log_dir is None:
            xdg_data_home = Path(Path.home() / '.local' / 'share')
            log_dir = xdg_data_home / 'chatsh_history'
        
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_file = self.log_dir / f"interaction_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.interactions: List[Interaction] = []
        self.next_id = 1
        
        # Initialize empty array if file doesn't exist
        if not self.current_file.exists():
            self.current_file.write_text('[\n]')

    def _get_next_id(self) -> int:
        current_id = self.next_id
        self.next_id += 1
        return current_id

    async def _append_interaction_to_file(self, interaction: Interaction) -> None:
        """Append an interaction to the JSON file with array items at column 0 but internal indentation"""
        # Format the interaction JSON with indentation
        interaction_json = json.dumps(interaction.to_dict(), indent=2)
        # The object itself starts at column 0, but its contents are indented 2 spaces
        formatted_interaction = interaction_json

        async with aiofiles.open(self.current_file, 'rb+') as f:
            # Read current size
            await f.seek(0, 2)  # Seek to end
            size = await f.tell()
            
            if size <= 3:  # File just has '[\n]'
                # For first item, write after opening [
                await f.seek(1)  # Position after [
                await f.write(f"\n{formatted_interaction}".encode())
                await f.write(b"\n]")
            else:
                # For subsequent items, add comma and newline after previous item
                await f.seek(size - 2)  # Position before \n]
                await f.write(f",\n{formatted_interaction}".encode())
                await f.write(b"\n]")

    async def add_interaction(self, 
                            type: InteractionType, 
                            content: str, 
                            metadata: Optional[Dict[str, Any]] = None,
                            parent_id: Optional[int] = None) -> int:
        """
        Add a new interaction to the log and write it to disk.
        Returns the interaction_id of the newly added interaction.
        """
        interaction_id = self._get_next_id()
        interaction = Interaction(
            type=type,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {},
            parent_id=parent_id,
            interaction_id=interaction_id
        )
        
        self.interactions.append(interaction)
        await self._append_interaction_to_file(interaction)
        
        return interaction_id

    async def record_user_message(self, message: str) -> int:
        """Record a user's input message."""
        return await self.add_interaction(
            type=InteractionType.USER_MESSAGE,
            content=message
        )

    async def record_llm_response(self, response: str, parent_id: int) -> int:
        """Record the LLM's response to a user message."""
        return await self.add_interaction(
            type=InteractionType.LLM_RESPONSE,
            content=response,
            parent_id=parent_id
        )

    async def record_code_execution_prompt(self, code: str, parent_id: int) -> int:
        """Record when the user is prompted about code execution."""
        return await self.add_interaction(
            type=InteractionType.CODE_EXECUTION_PROMPT,
            content=code,
            parent_id=parent_id
        )

    async def record_code_execution_decision(self, executed: bool, parent_id: int) -> int:
        """Record the user's decision about code execution."""
        return await self.add_interaction(
            type=InteractionType.CODE_EXECUTION_DECISION,
            content="executed" if executed else "skipped",
            metadata={"executed": executed},
            parent_id=parent_id
        )

    async def record_code_output(self, output: str, parent_id: int) -> int:
        """Record the output of executed code."""
        return await self.add_interaction(
            type=InteractionType.CODE_EXECUTION_OUTPUT,
            content=output,
            parent_id=parent_id
        )

    async def record_back_command(self, steps: int) -> int:
        """Record a back command and its effects."""
        return await self.add_interaction(
            type=InteractionType.BACK_COMMAND,
            content=f"Went back {steps} steps",
            metadata={"steps": steps}
        )

    async def record_exit(self, reason: str) -> int:
        """Record the conversation exit and reason."""
        return await self.add_interaction(
            type=InteractionType.EXIT_COMMAND,
            content=reason,
            metadata={"exit_type": "good_bot" if "good bot" in reason.lower() else "bad_bot"}
        )

    async def record_error(self, error: str, parent_id: Optional[int] = None) -> int:
        """Record an error that occurred during the conversation."""
        return await self.add_interaction(
            type=InteractionType.ERROR,
            content=str(error),
            parent_id=parent_id
        )

    async def record_system_message(self, message: str, parent_id: Optional[int] = None) -> int:
        """Record a system message or notification."""
        return await self.add_interaction(
            type=InteractionType.SYSTEM_MESSAGE,
            content=message,
            parent_id=parent_id
        )

    async def get_conversation_branch(self, interaction_id: int) -> List[Interaction]:
        """
        Get all interactions in a conversation branch leading to the specified interaction.
        """
        branch = []
        current_id = interaction_id
        
        # Create a map of id to interaction for faster lookup
        id_map = {i.interaction_id: i for i in self.interactions}
        
        while current_id is not None:
            if current_id not in id_map:
                break
            
            interaction = id_map[current_id]
            branch.insert(0, interaction)
            current_id = interaction.parent_id
            
        return branch

    @classmethod
    async def load_from_file(cls, file_path: Path) -> 'InteractionLog':
        """Load an interaction log from a file."""
        log = cls(log_dir=file_path.parent)
        
        async with aiofiles.open(file_path, 'r') as f:
            content = await f.read()
            # Parse as JSON array
            interactions_data = json.loads(content)
            
            for interaction_data in interactions_data:
                interaction = Interaction.from_dict(interaction_data)
                log.interactions.append(interaction)
                # Update next_id to be higher than any loaded id
                if interaction.interaction_id and interaction.interaction_id >= log.next_id:
                    log.next_id = interaction.interaction_id + 1
        
        return log

    def get_latest_interaction(self) -> Optional[Interaction]:
        """Get the most recent interaction in the log."""
        return self.interactions[-1] if self.interactions else None

    async def playback_conversation(self, start_id: Optional[int] = None) -> List[Interaction]:
        """
        Playback the conversation from the start or a specific interaction ID.
        Returns the sequence of interactions in chronological order.
        """
        if start_id is None:
            return self.interactions.copy()
        
        # Get the branch leading to start_id
        branch = await self.get_conversation_branch(start_id)
        
        # Find all subsequent interactions that branch from this path
        branch_ids = {i.interaction_id for i in branch}
        subsequent = [
            i for i in self.interactions 
            if i.timestamp > branch[-1].timestamp 
            and (i.parent_id in branch_ids or i.interaction_id in branch_ids)
        ]
        
        return branch + subsequent