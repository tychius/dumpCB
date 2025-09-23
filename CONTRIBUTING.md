# Contributing to dumpCB

Thank you for your interest in contributing! This guide will help you get started with development, code style, and submitting changes.

---

## Dev Environment Bootstrap

1. **Clone the repository:**
    ```bash
    git clone https://github.com/tychius/dumpCB.git
    cd dumpCB
    ```
2. **Create a virtual environment and install dependencies:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # or .\venv\Scripts\activate on Windows
    pip install -r requirements.txt
    ```
3. **Install pre-commit hooks:**
    ```bash
    pip install pre-commit
    pre-commit install
    ```

---

## Formatting & Linting

- **Code formatting:** [black](https://black.readthedocs.io/)
- **Linting:** [ruff](https://docs.astral.sh/ruff/)
- **Type checking:** [mypy](http://mypy-lang.org/) (strict mode)

Run all checks before committing:
```bash
black .
ruff .
mypy --strict .
```

---

## PR & Branching Guidelines

- Use feature branches for all changes (e.g., `feature/my-new-widget`).
- Keep PRs focused and small when possible.
- Write clear commit messages (commit-msg lint is enforced).
- Ensure all checks pass before requesting review.

---

## CODEOWNERS

Add yourself or others as maintainers for key folders below:

```
# CODEOWNERS
/app/services/ @tychius
/app/ui/ @tychius
/app/core/ @tychius
```

---

## Questions?
Open an issue or discussion on GitHub! 