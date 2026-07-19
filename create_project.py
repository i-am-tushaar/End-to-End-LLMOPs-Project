from pathlib import Path

# Current project folder
root = Path(".")

# Directories to create
folders = [
    "data",
    "multi_doc_chat",
    "multi_doc_chat/config",
    "multi_doc_chat/exception",
    "multi_doc_chat/logger",
    "multi_doc_chat/model",
    "multi_doc_chat/prompts",
    "multi_doc_chat/src",
    "multi_doc_chat/utils",
    "notebook",
    "static",
    "templates",
    "test"
]

# Files to create
files = [
    "main.py",
    "README.md",
    "requirements.txt",
    "pyproject.toml",
    ".gitignore",
    ".env",
    "templates/index.html",
    "static/styles.css"
]

# Create folders
for folder in folders:
    (root / folder).mkdir(parents=True, exist_ok=True)

# Create files
for file in files:
    file_path = root / file
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.touch(exist_ok=True)

print("✅ Project structure created successfully!")