import pytest
from unittest.mock import mock_open, patch
from datetime import datetime
from pathlib import Path
import re

# Import the functions to be tested
from chatsh.chat import chat  # Assuming the chat function is in a file named chat.py in the chatsh directory
from chatsh.chatsh import (
    extract_codes,
    handle_back_command,
    append_to_history,
    generate_system_description,
)

# Test for extract_codes function
def test_extract_codes():
    import inspect
    test_text = inspect.cleandoc("""
    Here's some code:
    ```sh
    echo "Hello, World!"
    ls -la
    ```
    And another code block:
    ```sh
    grep "pattern" file.txt
    ```
    """)
    expected_codes = [
        'echo "Hello, World!"\nls -la',
        'grep "pattern" file.txt'
    ]
    assert extract_codes(test_text) == expected_codes

# Test for handle_back_command function
def test_handle_back_command():
    chat_instance = chat("s")  # Create a mock chat instance

    # Test valid 'back' command
    assert handle_back_command("back 2", chat_instance) == True

    # Test valid 'b' command
    assert handle_back_command("b 1", chat_instance) == True

    # Test invalid command
    assert handle_back_command("invalid command", chat_instance) == False

# Test for append_to_history function
def test_append_to_history():
    mock_file = mock_open()
    with patch('builtins.open', mock_file):
        append_to_history('USER', 'Test message')

    mock_file().write.assert_called_once_with('<USER>\nTest message\n</USER>\n\n')

# Test for generate_system_description function
@patch('shutil.which')
def test_generate_system_description(mock_which):
    # Mock the behavior of shutil.which
    mock_which.side_effect = lambda cmd: cmd in ['rg', 'fd', 'jq']

    # Mock the get_shell function
    with patch('asyncio.run') as mock_run:
        mock_run.return_value = "Mock System Info"

        result = generate_system_description()

        assert "Mock System Info" in result
        assert "rg: faster replacement for grep" in result
        assert "fd: faster alternative to find" in result
        assert "jq: command-line JSON processor" in result
        assert "tldr: simplified man pages" not in result

# Test for chat instance creation
def test_chat_instance_creation():
    chat_inst = chat("s")
    assert chat_inst is not None


if __name__ == "__main__":
    pytest.main()


