# PyCharm Development Setup

## 1. Open Project

- File → Open → Select harbor directory
- PyCharm will detect the project structure automatically

## 2. Configure Python Interpreter

- File → Settings → Project: harbor → Python Interpreter
- Add Interpreter → Virtualenv Environment → New environment
- Location: `./venv`
- Base interpreter: Python 3.11+
- Check "Inherit global site-packages": False

## 3. Install Dependencies

```bash
# In PyCharm terminal
make dev
```

## 4. Configure Run Configurations

- Run → Edit Configurations
- Add New → Python
- Name: "Harbor Dev Server"
- Script path: app/main.py
- Environment variables: HARBOR_MODE=development

## 5. Enable Code Quality Tools

- Settings → Tools → External Tools
- Pre-commit hooks will run automatically
- Configure pytest as default test runner

## 6. Project Structure

PyCharm will recognize:

- app/ as source root
- tests/ as test root
- Type hints and docstring support enabled
