
# Project Architecture

## Overview
This project follows a modular architecture separating concerns into distinct packages:

## Directory Structure

```
Storage-builder/
├── motherbot/          # Mother bot implementation
│   ├── __init__.py
│   └── main.py         # Mother bot entry point
│
├── clonebot/           # Clone bot implementation  
│   ├── __init__.py
│   └── main.py         # Clone bot entry point
│
├── shared/             # Shared utilities
│   ├── utils/          # Common utilities
│   └── __init__.py
│
├── bot/                # Core bot functionality
│   ├── core/           # Core services
│   │   ├── config/     # Configuration management
│   │   ├── events/     # Event system
│   │   └── container.py # Dependency injection
│   │
│   ├── database/       # Database layer
│   │   ├── __init__.py
│   │   ├── clone_db.py
│   │   ├── users.py
│   │   └── ...
│   │
│   ├── programs/       # Reusable program modules
│   │   ├── __init__.py
│   │   ├── clone_admin.py
│   │   ├── clone_features.py
│   │   ├── clone_indexing.py
│   │   ├── clone_management.py
│   │   └── clone_random_files.py
│   │
│   ├── handlers/       # Request handlers
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── commands.py
│   │   └── ...
│   │
│   ├── plugins/        # Plugin system
│   │   ├── __init__.py
│   │   └── ...
│   │
│   └── utils/          # Bot utilities
│       ├── __init__.py
│       └── ...
│
├── tests/              # Test suite
├── web/                # Web interface
├── main.py             # Legacy entry point
├── run_motherbot.py    # Mother bot runner
└── run_clonebot.py     # Clone bot runner
```

## Key Concepts

### Programs
Programs are reusable modules that encapsulate specific functionality:
- **CloneAdminProgram**: Clone administration
- **CloneFeaturesProgram**: Feature management
- **CloneIndexingProgram**: File indexing
- **CloneManagementProgram**: Clone lifecycle
- **CloneRandomFilesProgram**: File browsing

Each program:
1. Has a clear responsibility
2. Registers its own handlers
3. Can be used in both mother and clone bots
4. Is independently testable

### Entry Points
- `run_motherbot.py`: Starts the mother bot
- `run_clonebot.py`: Starts the clone bot manager
- `main.py`: Legacy all-in-one entry point

### Database Layer
All database operations are centralized in `bot/database/`:
- `clone_db.py`: Clone management
- `users.py`: User management
- `subscription_db.py`: Subscriptions
- etc.

### Utilities
Common utilities in `bot/utils/`:
- `permissions.py`: Permission checking
- `security.py`: Security features
- `error_handler.py`: Error handling
- etc.

## Running the Project

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

## Testing
```bash
pytest tests/
```

## Benefits of This Structure

1. **Modularity**: Each component has a single responsibility
2. **Reusability**: Programs can be used across different bots
3. **Testability**: Each module can be tested independently
4. **Maintainability**: Clear organization makes code easier to maintain
5. **Scalability**: Easy to add new features without touching existing code
