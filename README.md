# dumpCB 
## Code Context Builder for AI Assistance

![Logo](assets/logo.ico)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Streamline your workflow by effortlessly gathering relevant code context for Large Language Models (LLMs) or other analysis tasks. `dumpCB` scans your project, intelligently filters files using `.gitignore` rules, and generates a clean, formatted context package, ready for use.

---

## Quick Navigation
- [Getting Started](#installation--setup-development)
- [Architecture](docs/ARCHITECTURE.md)
- [Extending](docs/EXTENDING.md)
- [Contributing](#contributing)

---

## Run in 60 Seconds (CLI Example)

```bash
# (Coming soon) Generate context for your project in one line:
dumpcb --project /path/to/your/project --output context.md
```

## Key Features

*   **Project Scanning:** Quickly scans a selected project folder.
*   **Intelligent Filtering:** Uses `.gitignore`, `.llmignore`, and default patterns to exclude irrelevant files.
*   **Binary File Detection:** Automatically skips common binary file types.
*   **Selective Context Generation:** Allows users to select specific files to include in the final context.
*   **Formatted Output:** Generates a clean, Markdown-formatted output including project structure and file contents.
*   **Modern UI:** Built with PySide6 for a responsive user experience.
*   **Customizable:** respects `.llmignore` for project-specific exclusion rules.
*   **Cross-Platform Potential:** Built with Python and Qt (though packaging currently focuses on Windows).

## Architecture at a Glance

(Placeholder for architecture diagram: ContextService ↔ Workers ↔ Controllers ↔ Widgets)

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for a detailed architecture overview.

## Screenshots

### Initial Application View

![Initial Application Interface](assets/dumpCB_v2.png)

When you first launch dumpCB, you're presented with a clean interface where you can select a project folder to analyze. The interface includes:
- Button to select your project folder
- Controls to select or deselect files once a project is loaded
- Action buttons that will become active after selection

---

### Project Analysis and Generated Context

![Project Analysis and Generated Context](assets/dumpCB_main.png)

After selecting a project folder and generating context:
1. **File Selection Area:** The top section displays checkboxes for including/excluding specific files in your context
2. **Generated Output:** The bottom section displays:
   - An organized project structure showing all selected files
   - Complete file contents with appropriate syntax formatting
   - Clean Markdown formatting for easy pasting into AI assistants

This formatted output makes it simple for AI tools to understand your code's structure and relationships, leading to more accurate assistance.

---

## Installation & Setup (Development)

To run or develop `dumpCB` locally, follow these steps:

1.  **Prerequisites:**
    *   Python 3.8+ (Recommended)
    *   `pip` (Python package installer)
    *   `git` (for cloning)

2.  **Clone the Repository:**
    ```bash
    git clone https://github.com/tychius/dumpCB.git
    cd dumpCB
    ```

3.  **Create and Activate a Virtual Environment:**
    *   **Windows:**
        ```bash
        python -m venv venv
        .\venv\Scripts\activate
        ```
    *   **macOS/Linux:**
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```

4.  **Install Dependencies:**
    ```bash
    pip install -e .
    ```

---

## Running the Application

Once the setup is complete, you can run the application directly from the source code:

```bash
python run_app.py
```

---

## Building the Executable (Windows)

To create a standalone `.exe` file for Windows:

1.  Ensure you have completed the Installation & Setup steps above.
2.  Install PyInstaller within your virtual environment:
    ```bash
    pip install pyinstaller
    ```
3.  Run the PyInstaller build command from the project root directory:
    ```bash
    python -m PyInstaller --onefile --windowed --icon=assets/logo.ico --name dumpCB run_app.py
    ```
    Notes:
    - The stylesheet and icon are embedded via Qt resources (`assets/resources.qrc` compiled into `assets/resources_rc.py`), so no `--add-data` flags are required.
    - If you change files under `assets/`, regenerate resources: `pyside6-rcc assets/resources.qrc -o assets/resources_rc.py`.
4.  The executable `dumpCB.exe` will be located in the `dist/` folder.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue.

## Acknowledgements

*   Built with the amazing [PySide6](https://www.qt.io/qt-for-python) library.
*   Uses [pathspec](https://pypi.org/project/pathspec/) for `.gitignore` style pattern matching.
