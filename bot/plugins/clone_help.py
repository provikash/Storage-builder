
"""
Clone-specific help and documentation
"""
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config
from bot.database.clone_db import get_clone_by_bot_token

logger = logging.getLogger(__name__)

def get_clone_id_from_client(client: Client):
    """Get clone ID from client"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
        if bot_token == Config.BOT_TOKEN:
            return None
        return bot_token.split(':')[0]
    except:
        return None

@Client.on_message(filters.command(['help', 'commands']) & filters.private)
async def clone_help_command(client: Client, message: Message):
    """Show help for clone bot commands"""
    try:
        clone_id = get_clone_id_from_client(client)
        if not clone_id:
            return  # Let mother bot handle this
        
        # Get clone data
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        if not clone_data:
            await message.reply_text("❌ Clone configuration not found.")
            return
        
        user_id = message.from_user.id
        is_admin = user_id == clone_data['admin_id']
        
        if is_admin:
            help_text = (
                f"🔧 **Clone Admin Commands**\n\n"
                f"**🗄️ Database & Indexing:**\n"
                f"• `/dbinfo` - Database information\n"
                f"• `/dbstats` - Database statistics\n"
                f"• `/dbtest` - Test database connection\n"
                f"• `/index <channel>` - Index channel media\n"
                f"• `/indexstats` - Indexing statistics\n\n"
                
                f"**🔍 Search & Files:**\n"
                f"• `/search <query>` - Search indexed files\n"
                f"• `/get <filename>` - Download file\n\n"
                
                f"**⚙️ Settings & Management:**\n"
                f"• `/clonesettings` - Clone settings panel\n"
                f"• `/cloneadmin` - Admin panel\n\n"
                
                f"**📊 Monitoring:**\n"
                f"• `/status` - Clone bot status\n"
                f"• `/stats` - Usage statistics\n\n"
                
                f"**💡 Features:**\n"
                f"• Auto-index forwarded media\n"
                f"• Dedicated MongoDB database\n"
                f"• Advanced search capabilities\n"
                f"• Download tracking\n\n"
                
                f"**Database:** `{clone_data.get('db_name', f'clone_{clone_id}')}`"
            )
            
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("⚙️ Clone Settings", callback_data="goto_clone_settings"),
                    InlineKeyboardButton("🗄️ Database Info", callback_data=f"refresh_db_info:{clone_id}")
                ],
                [
                    InlineKeyboardButton("📊 Statistics", callback_data=f"refresh_index_stats:{clone_id}"),
                    InlineKeyboardButton("🔧 Admin Panel", callback_data="goto_admin_panel")
                ],
                [
                    InlineKeyboardButton("📚 Documentation", callback_data="clone_documentation"),
                    InlineKeyboardButton("🆘 Support", callback_data="clone_support")
                ]
            ])
        else:
            help_text = (
                f"🔍 **Clone Bot Commands**\n\n"
                f"**🔍 Search & Download:**\n"
                f"• `/search <query>` - Search files\n"
                f"• `/get <filename>` - Download file\n\n"
                
                f"**📋 Information:**\n"
                f"• `/about` - About this bot\n"
                f"• `/help` - Show this help\n\n"
                
                f"**💡 How to use:**\n"
                f"1. Use `/search` to find files\n"
                f"2. Use `/get` to download files\n"
                f"3. Browse using bot buttons\n\n"
                
                f"**🤖 This is a clone bot with its own database.**"
            )
            
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔍 Try Search", switch_inline_query_current_chat="search "),
                    InlineKeyboardButton("📋 About Bot", callback_data="about_clone")
                ]
            ])
        
        await message.reply_text(help_text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error in clone help command: {e}")
        await message.reply_text("❌ Error showing help.")

@Client.on_message(filters.command(['about']) & filters.private)
async def clone_about_command(client: Client, message: Message):
    """Show about information for clone bot"""
    try:
        clone_id = get_clone_id_from_client(client)
        if not clone_id:
            return  # Let mother bot handle this
        
        # Get clone data
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        if not clone_data:
            await message.reply_text("❌ Clone configuration not found.")
            return
        
        # Get basic stats
        try:
            from bot.plugins.clone_search import get_clone_indexing_statistics
            stats = await get_clone_indexing_statistics(clone_data)
            
            if stats:
                files_info = f"📁 **Files:** {stats['total_files']:,} indexed ({stats['total_size_readable']})"
            else:
                files_info = "📁 **Files:** Database not accessible"
        except:
            files_info = "📁 **Files:** Statistics unavailable"
        
        about_text = (
            f"🤖 **About This Clone Bot**\n\n"
            f"**🆔 Clone Information:**\n"
            f"• Clone ID: `{clone_id}`\n"
            f"• Database: `{clone_data.get('db_name', f'clone_{clone_id}')}`\n"
            f"• Created: `{clone_data.get('created_at', 'Unknown').strftime('%Y-%m-%d') if hasattr(clone_data.get('created_at', None), 'strftime') else 'Unknown'}`\n\n"
            
            f"**📊 Statistics:**\n"
            f"{files_info}\n"
            f"🔍 **Search:** Advanced file search\n"
            f"📥 **Download:** Direct file access\n\n"
            
            f"**✨ Features:**\n"
            f"• Dedicated MongoDB database\n"
            f"• Auto-indexing from channels\n"
            f"• Advanced search capabilities\n"
            f"• Download tracking\n"
            f"• Admin control panel\n\n"
            
            f"**🛠️ Powered by Clone System**\n"
            f"Advanced bot hosting & management platform."
        )
        
        user_id = message.from_user.id
        is_admin = user_id == clone_data['admin_id']
        
        buttons = []
        if is_admin:
            buttons.extend([
                [
                    InlineKeyboardButton("⚙️ Settings", callback_data="goto_clone_settings"),
                    InlineKeyboardButton("🗄️ Database", callback_data=f"refresh_db_info:{clone_id}")
                ],
                [
                    InlineKeyboardButton("📊 Statistics", callback_data=f"refresh_index_stats:{clone_id}"),
                    InlineKeyboardButton("🔧 Admin Panel", callback_data="goto_admin_panel")
                ]
            ])
        
        buttons.extend([
            [
                InlineKeyboardButton("❓ Help", callback_data="clone_help"),
                InlineKeyboardButton("🆘 Support", callback_data="clone_support")
            ]
        ])
        
        reply_markup = InlineKeyboardMarkup(buttons) if buttons else None
        
        await message.reply_text(about_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in clone about command: {e}")
        await message.reply_text("❌ Error showing about information.")

@Client.on_message(filters.command(['status']) & filters.private)
async def clone_status_command(client: Client, message: Message):
    """Show clone bot status"""
    try:
        clone_id = get_clone_id_from_client(client)
        if not clone_id:
            return
        
        # Get clone data
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        if not clone_data:
            await message.reply_text("❌ Clone configuration not found.")
            return
        
        user_id = message.from_user.id
        is_admin = user_id == clone_data['admin_id']
        
        if not is_admin:
            await message.reply_text("❌ Only clone admin can check status.")
            return
        
        # Test database connectivity
        from bot.plugins.clone_database_commands import check_clone_database_connection
        db_connected, db_message = await check_clone_database_connection(clone_data)
        
        # Get quick stats
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            clone_client = AsyncIOMotorClient(clone_data['mongodb_url'])
            clone_db = clone_client[clone_data.get('db_name', f"clone_{clone_id}")]
            files_collection = clone_db['files']
            
            file_count = await files_collection.count_documents({})
            
            clone_client.close()
        except:
            file_count = "Error"
        
        status_text = (
            f"📊 **Clone Bot Status**\n\n"
            f"**🤖 Bot Information:**\n"
            f"• Clone ID: `{clone_id}`\n"
            f"• Status: `🟢 Active`\n"
            f"• Uptime: `Connected`\n\n"
            
            f"**🗄️ Database Status:**\n"
            f"• Connection: {'🟢 Connected' if db_connected else '🔴 Disconnected'}\n"
            f"• Database: `{clone_data.get('db_name')}`\n"
            f"• Indexed Files: `{file_count}`\n"
            f"• Response: {db_message}\n\n"
            
            f"**⚙️ Configuration:**\n"
            f"• Auto-Index: {'✅ On' if clone_data.get('auto_index_forwarded', True) else '❌ Off'}\n"
            f"• Random Files: {'✅ On' if clone_data.get('random_mode', True) else '❌ Off'}\n"
            f"• Recent Files: {'✅ On' if clone_data.get('recent_mode', True) else '❌ Off'}\n\n"
            
            f"**🔧 Admin:** @{message.from_user.username or 'Unknown'}"
        )
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_status:{clone_id}"),
                InlineKeyboardButton("🗄️ Database Test", callback_data=f"clone_test_db:{clone_id}")
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="goto_clone_settings"),
                InlineKeyboardButton("📊 Statistics", callback_data=f"refresh_index_stats:{clone_id}")
            ]
        ])
        
        await message.reply_text(status_text, reply_markup=buttons)
        
    except Exception as e:
        logger.error(f"Error in clone status command: {e}")
        await message.reply_text("❌ Error checking status.")
