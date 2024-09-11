from setuptools import setup, find_packages

setup(
    name="chatsh",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "aiofiles",
        "openai",
        "anthropic",
        "tiktoken",
        "google-generativeai",
    ],
    entry_points={
        "console_scripts": [
            "chatsh=chatsh:main",
        ],
    },
    include_package_data=True,
    package_data={
        "chatsh": ["system.prompt"],
    },
)