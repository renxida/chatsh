import pytest
from chatsh.chat import AnthropicChat, get_token

@pytest.fixture
def anthropic_chat():
    return AnthropicChat()

def test_anthropic_chat_initialization(anthropic_chat):
    assert isinstance(anthropic_chat, AnthropicChat)
    assert anthropic_chat.messages == []

@pytest.mark.asyncio
async def test_get_token():
    token = await get_token('anthropic')
    assert isinstance(token, str)
    assert len(token) > 0

# More tests can be added here later
