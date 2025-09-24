# Telegram Bot Project - File Sharing & Clone Management System

## Overview
This is a sophisticated Telegram bot system for file sharing with clone creation capabilities. It features a Mother Bot that can create and manage multiple clone bots, along with a web dashboard for monitoring and management.

## Project Status
**Import Status:** ✅ Successfully configured and running in Replit environment
**Last Updated:** September 24, 2025

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

## Recent Changes (2025-09-24)
- ✅ Fresh GitHub import successfully set up
- ✅ Python 3.11 environment configured
- ✅ All dependencies installed from requirements.txt
- ✅ Fixed logging issues in health monitoring
- ✅ Web server configured and running on port 5000
- ✅ VM deployment configuration set up
- ✅ Bot system fully operational with active users

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
- Web Dashboard: Available on port 5000
- Status: Fully operational with active users and monitoring systems
- Real users interacting with clone creation system