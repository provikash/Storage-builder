# Telegram Bot Project - File Sharing & Clone Management System

## Overview
This is a sophisticated Telegram bot system for file sharing with clone creation capabilities. It features a Mother Bot that can create and manage multiple clone bots, along with a web dashboard for monitoring and management.

## Project Status
**Import Status:** ✅ Successfully configured and running in Replit environment
**Last Updated:** October 4, 2025

## Architecture
- **Main Bot (Mother Bot):** Handles admin functions, clone creation, and premium subscriptions
- **Clone System:** Manages multiple child bots for different users  
- **Web Dashboard:** Flask-based monitoring interface on port 5000
- **Database:** MongoDB (configured with external MongoDB Atlas cluster)

## Key Features
- File sharing with secure access links
- Clone bot creation and management
- Premium subscription system with multiple pricing tiers
- Token verification system
- Admin panel and statistics
- Real-time monitoring dashboard
- Automatic subscription checking
- System health monitoring

## Technology Stack
- **Backend:** Python 3.11 with asyncio
- **Bot Framework:** Pyrogram (Pyrofork)
- **Database:** MongoDB with Motor (async driver)
- **Web Interface:** Flask
- **Deployment:** Replit VM (persistent)

## Recent Changes (2025-10-05)
- ✅ Fresh GitHub import successfully set up
- ✅ Python 3.11 environment configured
- ✅ All dependencies installed from requirements.txt
- ✅ Required secrets configured (API_ID, API_HASH, BOT_TOKEN, DATABASE_URL, ADMINS)
- ✅ Web server secured (removed hardcoded default secret key)
- ✅ **Consolidated all clone management into single clone_manager.py file**
- ✅ **Removed redundant clone files (clone_cli.py, run_clonebot.py, run_motherbot.py)**
- ✅ Cleaned up duplicate scripts and test files
- ✅ Updated .gitignore with project-specific entries
- ✅ VM deployment configuration set up for persistent operation
- ✅ Web server configured and running on port 5000
- ✅ Bot system fully operational with Mother Bot and clone bots

## Configuration
- Environment variables configured through Replit Secrets
- MongoDB connection established and tested
- Web server running on port 5000 with 0.0.0.0 binding
- VM deployment configured for persistent operation
- All workflows properly configured

## User Preferences
- Prefers working with existing project structure
- MongoDB configuration maintained (user's existing setup)
- Web dashboard functionality preserved

## Current State
- Mother Bot: @Hd_File_Sharing_bot (active)
- Clone Bots: 1 active (@Searchfilefreebot)
- Web Dashboard: Available on port 5000 (login required)
- Status: Fully operational with active users and monitoring systems
- Real users interacting with clone creation system

## Clone Management
All clone-related functionality has been consolidated into `clone_manager.py`. Use the CLI tool for all clone operations:
```bash
# List all clones and their status
python3 clone_manager.py list

# Start all clones
python3 clone_manager.py start-all

# Restart all clones
python3 clone_manager.py restart-all

# Stop all clones
python3 clone_manager.py stop-all

# Start specific clone
python3 clone_manager.py start --bot-id <BOT_ID>

# Restart specific clone
python3 clone_manager.py restart --bot-id <BOT_ID>

# Stop specific clone
python3 clone_manager.py stop --bot-id <BOT_ID>
```