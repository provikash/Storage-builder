# Mother Bot + Clone System

## Overview
This is a sophisticated Telegram bot system that functions as a "Mother Bot" with clone creation capabilities. The system includes file sharing, subscription management, admin panels, and a web dashboard.

## Project Architecture
- **Main Application**: `main.py` - Mother Bot + Clone System launcher
- **Bot Logic**: `bot/` directory containing plugins and database modules  
- **Web Dashboard**: `web/server.py` - Flask-based monitoring dashboard
- **Database**: MongoDB for bot data, PostgreSQL available for extensions

## Key Features
- 🤖 Mother Bot (@Hd_File_Sharing_bot) with admin capabilities
- 🔄 Clone bot creation and management system  
- 💰 Premium subscription system with crypto payments
- 📊 Web dashboard for monitoring (port 5000)
- 🔍 File search and sharing capabilities
- 🏥 Health monitoring and system stats
- 🔐 Token verification and security features

## Recent Changes (2025-09-08)
- ✅ Set up Python 3.11 environment with all dependencies
- ✅ Configured clean requirements.txt 
- ✅ Fixed web server to use port 5000 for Replit
- ✅ Set up deployment configuration for VM deployment
- ✅ Verified MongoDB connection and database setup

## User Preferences
- Language: Python 3.11
- Database: MongoDB (primary), PostgreSQL (available)
- Web Framework: Flask for dashboard
- Bot Framework: Pyrogram/Pyrofork for Telegram integration

## Current State
- ✅ Bot is running successfully
- ✅ Web dashboard accessible on port 5000
- ✅ Clone system operational (1 clone active)
- ✅ All dependencies installed and working
- ✅ Ready for production deployment

## Environment Setup
The project is configured for Replit environment with:
- DATABASE_URL: MongoDB connection
- BOT_TOKEN: Telegram bot token configured
- WEB_SERVER_PORT: 5000 (for Replit web view)
- All required API keys and configurations in place

## Commands
- Mother Bot: `/motheradmin` - Admin panel
- Clone Creation: `/createclone` - Create new clone bots
- Web Dashboard: Available at root URL (redirects to /dashboard)