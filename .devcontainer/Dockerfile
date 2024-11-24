FROM mcr.microsoft.com/vscode/devcontainers/python:3.12

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    poetry config virtualenvs.create false

# Create and set up non-root user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Add dev_tools to PATH
ENV PATH="/workspaces/chatsh/dev_tools:${PATH}"

# Set working directory
WORKDIR /workspaces/chatsh

# We'll mount the project files in devcontainer.json
# Install dependencies and project in editable mode during postCreateCommand
