
from pyrogram import Client, filters
from pyrogram.types import Message
from info import Config

@Client.on_message(filters.command("createclone") & filters.private)
async def debug_createclone_command(client: Client, message: Message):
    """Debug version of createclone command with comprehensive logging"""
    user_id = message.from_user.id
    
    print(f"🤖 DEBUG COMMAND: /createclone from user {user_id}")
    print(f"👤 DEBUG COMMAND: User details - ID: {user_id}, Username: @{message.from_user.username}, Name: {message.from_user.first_name}")
    print(f"📱 DEBUG COMMAND: Chat ID: {message.chat.id}")
    print(f"📝 DEBUG COMMAND: Full command: '{message.text}'")
    print(f"📋 DEBUG COMMAND: Command args: {message.command}")
    
    # Check admin status
    owner_id = getattr(Config, 'OWNER_ID', None)
    admins = getattr(Config, 'ADMINS', ())
    admin_list = list(admins) if isinstance(admins, tuple) else (admins if isinstance(admins, list) else [])
    if owner_id and owner_id not in admin_list:
        admin_list.append(owner_id)
    
    is_admin = user_id in admin_list or user_id == owner_id
    
    print(f"🔐 DEBUG COMMAND: createclone admin check - user_id: {user_id}, owner_id: {owner_id}, admins: {admins}, admin_list: {admin_list}")
    print(f"✅ DEBUG COMMAND: Is admin: {is_admin}")
    
    # Route to step_clone_creation
    try:
        from bot.plugins.step_clone_creation import createclone_command
        print(f"🔄 DEBUG COMMAND: Routing to step_clone_creation for user {user_id}")
        await createclone_command(client, message)
        print(f"✅ DEBUG COMMAND: Successfully routed createclone for user {user_id}")
    except Exception as e:
        print(f"❌ DEBUG COMMAND: Error routing createclone: {e}")
        await message.reply_text(f"❌ Error: {e}")

@Client.on_message(filters.command(["admin", "motheradmin"]) & filters.private)
async def debug_admin_command(client: Client, message: Message):
    """Debug admin command"""
    user_id = message.from_user.id
    
    print(f"🔧 DEBUG COMMAND: /admin or /motheradmin from user {user_id}")
    print(f"👤 DEBUG COMMAND: User details - ID: {user_id}, Username: @{message.from_user.username}")
    
    # Route to actual admin command
    try:
        from bot.plugins.admin_commands import admin_command
        print(f"🔄 DEBUG COMMAND: Routing to admin_commands for user {user_id}")
        await admin_command(client, message)
        print(f"✅ DEBUG COMMAND: Successfully routed admin command for user {user_id}")
    except Exception as e:
        print(f"❌ DEBUG COMMAND: Error routing admin command: {e}")
        await message.reply_text(f"❌ Admin command error: {e}")

@Client.on_message(filters.command("premium") & filters.private)
async def debug_premium_command(client: Client, message: Message):
    """Debug premium command"""
    user_id = message.from_user.id
    
    print(f"💎 DEBUG COMMAND: /premium from user {user_id}")
    print(f"👤 DEBUG COMMAND: User details - ID: {user_id}, Username: @{message.from_user.username}")
    
    # Route to actual premium command
    try:
        from bot.plugins.premium import premium_handler
        print(f"🔄 DEBUG COMMAND: Routing to premium handler for user {user_id}")
        await premium_handler(client, message)
        print(f"✅ DEBUG COMMAND: Successfully routed premium command for user {user_id}")
    except Exception as e:
        print(f"❌ DEBUG COMMAND: Error routing premium command: {e}")
        await message.reply_text(f"❌ Premium command error: {e}")

@Client.on_message(filters.command("help") & filters.private)
async def debug_help_command(client: Client, message: Message):
    """Debug help command"""
    user_id = message.from_user.id
    
    print(f"🔍 DEBUG: /help command received from user {user_id}")
    print(f"👤 DEBUG: User - ID: {user_id}, Username: @{message.from_user.username}")
    
    # Route to start_handler help
    try:
        from bot.plugins.start_handler import help_command
        print(f"🔄 DEBUG: Routing help command for user {user_id}")
        await help_command(client, message)
        print(f"✅ DEBUG: Help command routed successfully for user {user_id}")
    except Exception as e:
        print(f"❌ DEBUG: Error routing help command for user {user_id}: {e}")
        
        # Fallback help message
        help_text = """
❓ **Help & Support**

**🤖 Bot Commands:**
• `/start` - Start the bot
• `/help` - Show this help message
• `/stats` - View your statistics

**📞 Support:**
• Contact: @admin
• Status: Online 24/7

**🔧 Having Issues?**
• Try `/start` to refresh
• Contact support for help
        """
        await message.reply_text(help_textd: {e}")
        await message.reply_text(f"❌ Help command error: {e}")

# Add debug message for all unhandled commands
@Client.on_message(filters.command("*") & filters.private)
async def debug_unknown_commands(client: Client, message: Message):
    """Debug handler for unknown commands"""
    user_id = message.from_user.id
    command = message.command[0] if message.command else "unknown"
    
    # Skip known commands that are handled elsewhere
    known_commands = ["start", "createclone", "admin", "motheradmin", "premium", "help", "about", "stats", "broadcast", "ban", "unban"]
    
    if command.lower() in known_commands:
        return
    
    print(f"❓ DEBUG COMMAND: Unknown command '/{command}' from user {user_id}")
    print(f"👤 DEBUG COMMAND: User details - ID: {user_id}, Username: @{message.from_user.username}")
    print(f"📝 DEBUG COMMAND: Full text: '{message.text}'")
