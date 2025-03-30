# dumpCB - Context Builder Assistant

![Logo](assets/logo.ico) <!-- Optional: If your logo looks good rendered directly -->

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) <!-- Example license badge -->

A simple desktop application built with Python and PySide6 to help developers quickly gather and format code context from a project directory, respecting `.gitignore` and `.llmignore` rules, and filtering out binary files.

---

## Key Features

*   **Project Scanning:** Quickly scans a selected project folder.
*   **Intelligent Filtering:** Uses `.gitignore`, `.llmignore`, and default patterns to exclude irrelevant files.
*   **Binary File Detection:** Automatically skips common binary file types.
*   **Selective Context Generation:** Allows users to select specific files to include in the final context.
*   **Formatted Output:** Generates a clean, Markdown-formatted output including project structure and file contents.
*   **Modern UI:** Built with PySide6 for a responsive user experience.
*   **Customizable:** respects `.llmignore` for project-specific exclusion rules.
*   **Cross-Platform Potential:** Built with Python and Qt (though packaging currently focuses on Windows).

## Screenshots

*(Add screenshots here later to showcase the application)*

```
<!-- Example: -->
<!-- ![Main Window](docs/images/screenshot_main.png) -->
<!-- ![File Selection](docs/images/screenshot_selection.png) -->
```

---

## Installation & Setup (Development)

To run or develop `dumpCB` locally, follow these steps:

1.  **Prerequisites:**
    *   Python 3.8+ (Recommended)
    *   `pip` (Python package installer)
    *   `git` (for cloning)

2.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url> # Replace with your repo URL later
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
    pip install -r requirements.txt
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
    python -m PyInstaller --onefile --windowed --icon=assets/logo.ico --add-data "app/ui/style.qss;app/ui" --add-data "assets;assets" run_app.py --name dumpCB
    ```
4.  The executable `dumpCB.exe` will be located in the `dist/` folder.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. *(You'll need to create a LICENSE file)*

---

## Contributing

*(Optional: Add guidelines if you want contributions)*

Contributions are welcome! Please feel free to submit a pull request or open an issue.

## Acknowledgements

*(Optional: Mention any libraries/inspirations you want to credit)*

*   Built with the amazing [PySide6](https://www.qt.io/qt-for-python) library.
*   Uses [pathspec](https://pypi.org/project/pathspec/) for `.gitignore` style pattern matching.

## Project Structure

```
dropCBAI/
├── app/                  # Main application package
│   ├── __init__.py
│   ├── core/             # Core processing logic
│   │   ├── __init__.py
│   │   ├── file_processor.py # Finds relevant files
│   │   ├── formatter.py      # Formats the output string
│   │   ├── ignore_handler.py # Handles .gitignore/.llmignore logic
│   │   └── main_processor.py # Orchestrates core tasks
│   ├── ui/               # User interface components
│   │   ├── __init__.py
│   │   └── main_window.py  # Main application window (CustomTkinter)
│   ├── utils/            # Utility functions
│   │   ├── __init__.py
│   │   └── file_utils.py   # File reading, encoding, language detection
│   └── config/           # Configuration files
│       ├── __init__.py
│       └── constants.py    # Default ignores, language map
├── main.py               # Application entry point
├── requirements.txt      # Python dependencies
└── README.md             # This file
``` 