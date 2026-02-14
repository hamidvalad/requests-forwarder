# Contributing

Thank you for considering contributing to **requests-forwarder**! 🎉

## How to contribute

### 1. Fork & clone

```bash
git clone https://github.com/hamidvalad/requests-forwarder.git
cd requests-forwarder
```

### 2. Create a virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install dev dependencies

```bash
pip install -e ".[dev]"
```

### 4. Make your changes

- Create a feature branch: `git checkout -b my-feature`
- Write code + tests.
- Run the test suite: `pytest`
- Run the linter: `ruff check .`

### 5. Submit a Pull Request

- Push your branch and open a PR against `main`.
- Describe what changed and why.
- Make sure all tests pass.

## Code style

- Follow [PEP 8](https://peps.python.org/pep-0008/).
- Use type hints where possible.
- Write docstrings for public functions.
- Keep commits small and focused.

## Reporting bugs

Open an [issue](https://github.com/hamidvalad/requests-forwarder/issues) with:

1. Python version (`python --version`)
2. `pyTelegramBotAPI` version (`pip show pyTelegramBotAPI`)
3. Steps to reproduce
4. Expected vs actual behavior

## License

By contributing, you agree that your contributions will be licensed under the
[MIT License](LICENSE).
