# Telegram Bot Project - File Sharing & Clone Management System

## Overview
This is a sophisticated Telegram bot system for file sharing with clone creation capabilities. It features a Mother Bot that can create and manage multiple clone bots, along with a web dashboard for monitoring and management.

## Project Status
**Import Status:** ✅ Successfully configured and running in Replit environment

## Architecture
- **Main Bot (Mother Bot):** Handles admin functions, clone creation, and premium subscriptions
- **Clone System:** Manages multiple child bots for different users
- **Web Dashboard:** Flask-based monitoring interface on port 5000
- **Database:** MongoDB (configured with external MongoDB Atlas cluster)

## Key Features
- File sharing with secure access links
- Clone bot creation and management
- Premium subscription system
- Token verification system  
- Admin panel and statistics
- Real-time monitoring dashboard
- Automatic subscription checking

## Technology Stack
- **Backend:** Python 3.11 with asyncio
- **Bot Framework:** Pyrogram (Pyrofork)
- **Database:** MongoDB with Motor (async driver)
- **Web Interface:** Flask
- **Deployment:** Replit VM (persistent)

## Recent Changes (2024-09-09)
- ✅ Installed all Python dependencies
- ✅ Fixed web server configuration (WEB_PORT → WEB_SERVER_PORT)
- ✅ Configured for VM deployment
- ✅ Bot is running successfully with web dashboard active

## Configuration
- Environment variables configured through Replit Secrets
- MongoDB connection established
- Web server running on port 5000
- VM deployment configured for persistent operation

## User Preferences
- Prefers working with existing project structure
- MongoDB configuration maintained (user's existing setup)
- Web dashboard functionality preserved

## Current State
- Mother Bot: @Hd_File_Sharing_bot
- Web Dashboard: Available on port 5000
- Status: Fully operational with monitoring systems active