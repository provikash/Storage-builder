
# Code Migration Guide

## New Structure

The codebase has been reorganized into a cleaner architecture:

### Handlers (`bot/handlers/`)
Request handlers organized by bot type:
- `motherbot/` - Mother bot specific handlers
- `clonebot/` - Clone bot specific handlers  
- `shared/` - Handlers used by both bots

### Programs (`bot/programs/`)
Reusable program modules:
- `clone_admin.py` - Clone administration
- `clone_features.py` - Feature management
- `clone_indexing.py` - File indexing
- `clone_management.py` - Clone lifecycle
- `clone_random_files.py` - File browsing

### Legacy Plugins (`bot/plugins/`)
Old plugins being phased out. New code should go in `handlers/` or `programs/`.

## Migration Status

Files to migrate from `bot/plugins/` to new structure:

### To `bot/handlers/motherbot/`:
- `admin_panel.py` → `admin_panel.py`
- `broadcast.py` → `broadcast.py`
- `step_clone_creation.py` → `clone_creation.py`
- `stats.py` → `statistics.py`
- `mother_admin.py` → `admin.py`
- `mother_bot_commands.py` → `commands.py`

### To `bot/handlers/clonebot/`:
- `clone_admin_unified.py` → `admin.py`
- `clone_search_unified.py` → `search.py`
- `clone_indexing_unified.py` → `indexing.py`
- `clone_random_files.py` → Use `bot/programs/clone_random_files.py`

### To `bot/handlers/shared/`:
- `commands_unified.py` → `commands.py`
- `premium.py` → `premium.py`
- `token.py` → `verification.py`
- `referral_program.py` → `referral.py`
- `balance_management.py` → `balance.py`

### To Delete (Duplicates/Obsolete):
- `clone_database_commands.py` (merged into handlers)
- `clone_force_commands.py` (merged into handlers)
- `clone_status_commands.py` (merged into handlers)
- `clone_token_commands.py` (merged into handlers)
- `debug_*.py` files (move to `tests/` if needed)
- `simple_test_commands.py` (move to `tests/`)
- `missing_commands.py` (obsolete)
- `handler_registry.py` (replaced by proper structure)

## Next Steps

1. Move files to new locations as listed above
2. Update imports in moved files
3. Test functionality after each migration
4. Remove old files once migration is verified
5. Update documentation
