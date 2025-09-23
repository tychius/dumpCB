# Default patterns to ignore files and directories
# Based on common .gitignore patterns
DEFAULT_IGNORE_PATTERNS = [
    # Git specific
    ".git/",
    ".gitignore",
    ".gitattributes",
    ".gitmodules",

    # Python specific
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    ".Python",
    "build/",
    "develop-eggs/",
    "dist/",
    "downloads/",
    "eggs/",
    ".eggs/",
    "lib/",
    "lib64/",
    "parts/",
    "sdist/",
    "var/",
    "wheels/",
    "share/python-wheels/",
    "*.egg-info/",
    ".installed.cfg",
    "*.egg",
    "MANIFEST",

    # Virtual environments
    "env/",
    "venv/",
    ".env/",
    ".venv/",
    "ENV/",
    "VENV/",
    ".direnv/",

    # IDE and Editor specific
    ".vscode/",
    ".idea/",
    "*.suo",
    "*.ntvs*",
    "*.njsproj",
    "*.sln",
    "*.swp",
    "*~",

    # OS specific
    ".DS_Store",
    "Thumbs.db",

    # Dependency lock files
    "package-lock.json",
    "yarn.lock",
    "composer.lock",
    "Gemfile.lock",
    "Pipfile.lock",
    "poetry.lock",

    # Build artifacts & Metadata
    ".github/",
    ".gitlab-ci.yml",
    "firebase.json",
    "netlify.toml",
    ".firebaserc",

    # Other common ignores
    "node_modules/",
    "logs/",
    "*.log",
    "tmp/",
    "temp/",
    "*.tmp",
    ".llmignore", # Ignore the ignore file itself

    # C# / .NET
    "bin/", "obj/", ".vs/", "packages/", "TestResults/",
    "*.csproj.user", "*.suo", "*.nupkg",

    # Image files (added for default ignore)
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.ico",
    "*.svg",
    # Generated Qt resource files
    "*resources_rc.py",
]

# Directories to ALWAYS ignore during the initial structural scan
# These should be patterns that match directories only
# NOTE: This list overlaps with DEFAULT_IGNORE_PATTERNS but focuses on directories
# known to be large or irrelevant for the initial scan, speeding it up.
# The full DEFAULT_IGNORE_PATTERNS are applied later when filtering selected files.
ESSENTIAL_DIR_IGNORE_PATTERNS = [
    ".git/",
    "__pycache__/",
    "build/",
    "dist/",
    "env/",
    "venv/",
    ".env/",
    ".venv/",
    "ENV/",
    "VENV/",
    ".vscode/", # Often contains large caches/extensions
    ".idea/",   # Often contains caches/indices
    "node_modules/",
    "vendor/", # Common for PHP/Ruby dependencies
    "target/", # Common for Java/Rust builds
    # Add other notoriously large/irrelevant directories here
]

# File extensions mapping to Markdown language identifiers
LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".java": "java",
    ".kt": "kotlin",
    ".swift": "swift",
    ".c": "c",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".go": "go",
    ".php": "php",
    ".rb": "ruby",
    ".rs": "rust",
    ".sh": "bash",
    ".ps1": "powershell",
    ".sql": "sql",
    ".md": "markdown",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".xml": "xml",
    ".dockerfile": "dockerfile",
    "Dockerfile": "dockerfile",
    # Add more mappings as needed
} 