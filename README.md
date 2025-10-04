# Storage-builder

## Project Structure

This project is organized into three main components:

- **motherbot/** - Mother bot logic and plugins
- **clonebot/** - Clone bot management and clone-specific features  
- **shared/** - Shared utilities, database, and common plugins

## Running the Bots

### Mother Bot
```bash
python run_motherbot.py
```

### Clone Bot System
```bash
python run_clonebot.py
```

### All-in-One (Legacy)
```bash
python main.py
```

## Windows Support

For Windows users, use the Windows-specific requirements:
```bash
pip install -r requirements_windows.txt
```

This excludes uvloop which is not compatible with Windows.

# Storage-builder