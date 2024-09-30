import pytest
from unittest.mock import patch, mock_open
from chatsh.chat import AnthropicChat, get_token
import os
import io
import sys

@pytest.fixture
def anthropic_chat():
    return AnthropicChat()

def test_anthropic_chat_initialization(anthropic_chat):
    assert isinstance(anthropic_chat, AnthropicChat)
    assert anthropic_chat.messages == []

@pytest.mark.asyncio
@patch('os.path.expanduser')
@patch('aiofiles.open')
async def test_get_token(mock_aiofiles_open, mock_expanduser):
    mock_expanduser.return_value = "/mock/home"
    mock_file = mock_open(read_data="mock_token_123")
    mock_aiofiles_open.return_value.__aenter__.return_value.read.return_value = "mock_token_123"

    # Test successful token read
    token = await get_token('anthropic')
    mock_expanduser.assert_called_once_with('~')
    mock_aiofiles_open.assert_called_once_with("/mock/home/.config/anthropic.token", 'r')
    assert token == "mock_token_123"

    # Reset mocks
    mock_expanduser.reset_mock()
    mock_aiofiles_open.reset_mock()

    # Test when the file doesn't exist for a non-Anthropic vendor
    mock_aiofiles_open.side_effect = FileNotFoundError
    with pytest.raises(Exception):
        await get_token('openai')

    # Test when the file doesn't exist for Anthropic
    captured_output = io.StringIO()
    sys.stdout = captured_output
    with pytest.raises(Exception):
        await get_token('anthropic')
    sys.stdout = sys.__stdout__
    
    assert "Error reading anthropic.token file:" in captured_output.getvalue()

# More tests can be added here later
