# Overview

This is a Mother Bot + Clone System built with Python/Pyrogram that enables creating and managing multiple Telegram bot clones. The system consists of a main "mother bot" that can spawn and manage multiple clone bots, each with their own database and subscription system. The platform includes features like file sharing, search functionality, subscription management, and a comprehensive admin panel.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Core Components

**Mother Bot Architecture**: The system uses a hub-and-spoke model where a single mother bot manages multiple clone instances. Each clone operates independently with its own database and configuration while being centrally managed.

**Clone Management System**: Implemented through `CloneManager` class that handles creation, starting, stopping, and monitoring of clone bot instances. Each clone can be configured with different features and subscription tiers.

**Database Layer**: Uses MongoDB with Motor (async driver) for data persistence. Separate collections handle users, clones, subscriptions, premium features, file indexing, and balance management. Each clone can optionally have its own database instance.

**Session Management**: Implements user session tracking and expiration through `SessionManager` to handle user state across interactions.

**Subscription System**: Multi-tier subscription model supporting monthly, quarterly, semi-annual, and yearly plans ranging from $3-26. Includes payment verification and automatic expiry handling.

**File Management**: Advanced file sharing system with batch operations, search indexing, and secure link generation. Files are stored in designated database channels with metadata indexing.

**Security Layer**: Input validation, admin verification decorators, and protected configuration attributes prevent unauthorized access and injection attacks.

## Key Design Patterns

**Plugin Architecture**: Modular command handlers organized in separate plugin files for maintainability and feature isolation.

**Async-First Design**: Leverages asyncio throughout for concurrent operations, essential for managing multiple bot instances simultaneously.

**Configuration Management**: Environment-based configuration with runtime protection for sensitive values like tokens and admin IDs.

**Balance System**: Integrated wallet functionality allowing users to purchase clone creation and premium features.

**Admin Panel System**: Hierarchical admin access with Mother Bot admins having global control and Clone Bot admins having instance-specific control.

## Technical Decisions

**Pyrogram Framework**: Chosen over python-telegram-bot for better async support and more flexible message handling required for clone management.

**Motor/MongoDB**: Selected for its async capabilities and flexible document structure suitable for varying clone configurations.

**Token-Based Authentication**: Implements verification tokens with expiration for user access control without requiring external OAuth.

**Scheduled Tasks**: Uses APScheduler for subscription monitoring, clone health checks, and automated cleanup operations.

**Web Interface**: Optional Flask web server for monitoring dashboards and health checks.

# External Dependencies

## Core Services
- **MongoDB**: Primary database for all persistent data storage
- **Telegram Bot API**: Communication layer through Pyrogram framework
- **APScheduler**: Task scheduling for subscription management and cleanup

## Third-Party APIs
- **Shortlink Services**: For generating shortened file sharing links (configurable API)
- **Payment Processing**: Integration points for subscription payments (implementation varies)

## Python Libraries
- **pyrofork**: Enhanced Pyrogram fork for advanced Telegram bot features  
- **motor**: Async MongoDB driver for database operations
- **uvloop**: High-performance event loop for async operations
- **cryptography/TgCrypto**: Encryption for secure file transfers
- **python-dotenv**: Environment variable management
- **psutil**: System monitoring and resource tracking
- **flask**: Optional web interface for monitoring
- **dnspython**: DNS resolution for MongoDB connections

## Development Tools
- **pytest**: Testing framework with async support
- **pytest-mock**: Mocking utilities for testing
- **logging**: Comprehensive logging with rotation support

## Optional Integrations
- **Web Monitoring**: Health check endpoints for external monitoring
- **Payment Gateways**: Configurable payment processing for subscriptions
- **Analytics**: User behavior and system performance tracking