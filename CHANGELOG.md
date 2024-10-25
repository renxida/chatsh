# Changelog

## v0.3.0

### Core
- Refactored conversation history management into dedicated ConversationHistory class
- Fixed backtracking functionality to properly handle conversation state 
- Removed OpenAI and Gemini chat implementations to focus on Anthropic/Claude
- Updated Claude model to sonnet-20241022

### UI/UX
- Added demo GIF to README
- Added FAQ section to documentation
- Improved error handling and state management

### Build
- Removed poetry.lock for better dependency flexibility
- Updated Python compatibility to >=3.8.1,<4.0
- Updated Textual to v0.83.0

## v0.2.0
Initial public release

## v0.1.1, v0.1.2 
Early development versions
