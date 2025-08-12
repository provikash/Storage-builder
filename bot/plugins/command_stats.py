
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.database import get_command_stats
from bot.utils.command_verification import check_command_limit
from info import Config

@Client.on_message(filters.command("mystats") & filters.private)
async def my_stats_command(client: Client, message: Message):
    """Show user's command usage stats"""
    user_id = message.from_user.id
    
    try:
        stats = await get_command_stats(user_id)
        needs_verification, remaining = await check_command_limit(user_id)
        
        status_text = "🔥 **Unlimited**" if remaining == -1 else f"🆓 **{remaining}/3**" if remaining > 0 else "❌ **Limit Reached**"
        
        stats_text = f"""📊 **Your Command Usage Stats**

👤 **User:** {message.from_user.first_name}
🎯 **Current Status:** {status_text}
📈 **Total Commands Used:** {stats['command_count']}

⏰ **Last Command:** {stats['last_command_at'].strftime('%Y-%m-%d %H:%M UTC') if stats['last_command_at'] else 'Never'}
🔄 **Last Reset:** {stats['last_reset'].strftime('%Y-%m-%d %H:%M UTC') if stats['last_reset'] else 'Never'}

💡 **Get Premium** for unlimited access without verification!"""
        
        await message.reply_text(stats_text)
        
    except Exception as e:
        print(f"ERROR in mystats command: {e}")
        await message.reply_text("❌ Error retrieving stats. Please try again later.")
