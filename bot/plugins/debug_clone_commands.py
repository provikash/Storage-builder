
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
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

@Client.on_message(filters.command(['testcommands', 'debugcommands']) & filters.private)
async def test_clone_commands(client: Client, message: Message):
    """Test if clone commands are working"""
    try:
        clone_id = get_clone_id_from_client(client)
        if not clone_id:
            await message.reply_text("❌ This command is only available in clone bots.")
            return
        
        # Get clone data to verify admin
        clone_data = await get_clone_by_bot_token(getattr(client, 'bot_token'))
        if not clone_data:
            await message.reply_text("❌ Clone configuration not found.")
            return
        
        # Check if user is admin of this clone
        if message.from_user.id != clone_data['admin_id']:
            await message.reply_text("❌ Only clone admin can use this command.")
            return
        
        # Test response
        await message.reply_text(
            f"✅ **Clone Commands Test**\n\n"
            f"🤖 **Clone ID**: `{clone_id}`\n"
            f"👤 **Admin ID**: `{clone_data['admin_id']}`\n"
            f"🗄️ **Database**: `{clone_data.get('db_name', 'Not set')}`\n"
            f"🔗 **MongoDB URL**: `{'✅ Configured' if clone_data.get('mongodb_url') else '❌ Not configured'}`\n\n"
            f"📋 **Available Commands**:\n"
            f"• `/testdb` - Test database connection\n"
            f"• `/dbstats` - View database statistics\n"
            f"• `/autoindex` - Toggle auto-indexing\n"
            f"• `/batchindex <channel>` - Batch index channel\n"
            f"• `/bulkindex <channel>` - Bulk index large channels\n\n"
            f"🔧 **Commands are working!**"
        )
        
    except Exception as e:
        logger.error(f"Error in test commands: {e}")
        await message.reply_text(f"❌ Error testing commands: {str(e)}")

@Client.on_message(filters.command(['quicktest']) & filters.private)
async def quick_test_command(client: Client, message: Message):
    """Quick test command that always responds"""
    try:
        clone_id = get_clone_id_from_client(client)
        await message.reply_text(
            f"🚀 **Quick Test Response**\n\n"
            f"✅ Commands are working!\n"
            f"📱 Clone ID: `{clone_id or 'Mother Bot'}`\n"
            f"👤 User ID: `{message.from_user.id}`\n"
            f"🕒 Time: `{message.date}`"
        )
    except Exception as e:
        logger.error(f"Error in quick test: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")
