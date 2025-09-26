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

# Removed duplicate help command handler to prevent conflicts with start_handler.py
# The help command is properly handled in start_handler.pylp command for user {user_id}: {e}")
# await message.reply_text(f"❌ Help command error: {e}")

# Add debug message for all unhandled commands
@Client.on_message(filters.command(["debug", "test", "status"]))
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


@Client.on_message(filters.command("debugclones") & filters.private)
async def debug_clones_command(client: Client, message: Message):
    """Debug command to check clone status"""
    user_id = message.from_user.id
    
    if user_id not in Config.ADMINS:
        return await message.reply_text("❌ Only admins can use this command.")
    
    try:
        from bot.database.clone_db import get_all_clones
        all_clones = await get_all_clones()
        
        if not all_clones:
            await message.reply_text("❌ No clones found in database.")
            return
        
        text = "🤖 **Clone Database Status:**\n\n"
        for clone in all_clones:
            bot_id = clone.get('_id', 'Unknown')
            username = clone.get('username', 'Unknown')
            status = clone.get('status', 'Unknown')
            admin_id = clone.get('admin_id', 'Unknown')
            
            text += f"🤖 **{username}** (`{bot_id}`)\n"
            text += f"   Status: {status}\n"
            text += f"   Admin: {admin_id}\n\n"
        
        await message.reply_text(text)
        
    except Exception as e:
        await message.reply_text(f"❌ Error checking clones: {e}")



@Client.on_message(filters.command("activateclone") & filters.private)
async def activate_clone_command(client: Client, message: Message):
    """Activate a clone bot"""
    user_id = message.from_user.id
    
    if user_id not in Config.ADMINS:
        return await message.reply_text("❌ Only admins can use this command.")
    
    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/activateclone <bot_id>`")
    
    bot_id = message.command[1]
    
    try:
        from bot.database.clone_db import get_clone, activate_clone
        from clone_manager import clone_manager
        
        clone = await get_clone(bot_id)
        if not clone:
            return await message.reply_text(f"❌ Clone {bot_id} not found.")
        
        # Activate in database
        await activate_clone(bot_id)
        
        # Start the clone
        success, msg = await clone_manager.start_clone(bot_id)
        
        if success:
            await message.reply_text(f"✅ Clone {bot_id} activated and started: {msg}")
        else:
            await message.reply_text(f"⚠️ Clone {bot_id} activated in DB but failed to start: {msg}")
            
    except Exception as e:
        await message.reply_text(f"❌ Error activating clone: {e}")



@Client.on_message(filters.command("forcestartall") & filters.private)
async def force_start_all_clones_command(client: Client, message: Message):
    """Force start all clones regardless of status"""
    user_id = message.from_user.id
    
    if user_id not in Config.ADMINS:
        return await message.reply_text("❌ Only admins can use this command.")
    
    try:
        from bot.database.clone_db import get_all_clones, activate_clone
        from clone_manager import clone_manager
        
        all_clones = await get_all_clones()
        if not all_clones:
            return await message.reply_text("❌ No clones found in database.")
        
        status_msg = await message.reply_text("🔄 Force starting all clones...")
        
        started_count = 0
        total_count = len(all_clones)
        
        for clone in all_clones:
            bot_id = clone.get('_id')
            username = clone.get('username', 'Unknown')
            current_status = clone.get('status', 'unknown')
            
            try:
                # Force activate in database first
                await activate_clone(bot_id)
                
                # Try to start the clone
                success, msg = await clone_manager.start_clone(bot_id)
                
                if success:
                    started_count += 1
                    logger.info(f"✅ Force started clone {username}: {msg}")
                else:
                    logger.error(f"❌ Failed to force start clone {username}: {msg}")
                    
            except Exception as e:
                logger.error(f"❌ Error force starting clone {username}: {e}")
        
        await status_msg.edit_text(
            f"🎉 **Force Start Complete**\n\n"
            f"✅ Started: {started_count}/{total_count} clones\n"
            f"❌ Failed: {total_count - started_count} clones"
        )
        
    except Exception as e:
        await message.reply_text(f"❌ Error force starting clones: {str(e)}")
