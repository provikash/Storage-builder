
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from info import Config
from bot.database.referral_db import (
    create_referral_code, get_referral_code, get_referrer_by_code, 
    record_referral, get_referral_stats, get_top_referrers
)
from bot.database.balance_db import get_user_balance
from bot.database.premium_db import is_premium_user
from bot.logging import LOGGER

logger = LOGGER(__name__)

# Store referral sessions
referral_sessions = {}

@Client.on_message(filters.command("referral") & filters.private)
async def referral_command(client: Client, message: Message):
    """Show referral program information"""
    user_id = message.from_user.id
    
    # Check if this is mother bot
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    if bot_token != Config.BOT_TOKEN:
        await message.reply_text("🤖 **Referral Program**\n\nThe referral program is only available in the Mother Bot, not in clone bots.")
        return
    
    # Create referral code if doesn't exist
    referral_code = await get_referral_code(user_id)
    if not referral_code:
        referral_code = await create_referral_code(user_id)
    
    if not referral_code:
        await message.reply_text("❌ Error creating referral code. Please try again later.")
        return
    
    # Get user stats
    stats = await get_referral_stats(user_id)
    balance = await get_user_balance(user_id)
    is_premium = await is_premium_user(user_id)
    
    # Create referral URL
    bot_username = client.me.username
    referral_url = f"https://t.me/{bot_username}?start=ref_{referral_code}"
    
    text = f"🎁 **Referral Program**\n\n"
    text += f"💰 **Earn $0.10 for every premium purchase!**\n\n"
    text += f"🔗 **Your Referral Link:**\n"
    text += f"`{referral_url}`\n\n"
    text += f"📊 **Your Stats:**\n"
    text += f"• 👥 Total Referrals: {stats['total_referrals'] if stats else 0}\n"
    text += f"• 💵 Total Earnings: ${stats['total_earnings'] if stats else 0:.2f}\n"
    text += f"• ⏳ Pending Rewards: {stats['pending_rewards'] if stats else 0}\n"
    text += f"• ✅ Paid Rewards: {stats['paid_rewards'] if stats else 0}\n\n"
    text += f"💰 **Current Balance:** ${balance:.2f}\n"
    text += f"💎 **Premium Status:** {'✅ Active' if is_premium else '❌ Not Active'}\n\n"
    text += f"📋 **How it works:**\n"
    text += f"1. Share your referral link\n"
    text += f"2. When someone joins and buys premium\n"
    text += f"3. You get $0.10 added to your balance\n"
    text += f"4. Use earnings to create more clones!"
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Detailed Stats", callback_data="referral_detailed_stats"),
            InlineKeyboardButton("🏆 Leaderboard", callback_data="referral_leaderboard")
        ],
        [
            InlineKeyboardButton("📱 Share Link", callback_data="referral_share_link"),
            InlineKeyboardButton("💡 Tips & Tricks", callback_data="referral_tips")
        ],
        [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
    ])
    
    await message.reply_text(text, reply_markup=buttons)

# DISABLED: Referral start handler moved to main start_handler.py to avoid conflicts
# Referral logic can be integrated into the main start command when neededeate your own clone bot!"
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Create My Clone", callback_data="start_clone_creation")],
            [InlineKeyboardButton("💎 View Premium Plans", callback_data="premium_info")]
        ])
        
        await message.reply_text(text, reply_markup=buttons)
        
        # Notify referrer
        try:
            await client.send_message(
                referrer_id,
                f"🎉 **New Referral!**\n\n"
                f"Someone just joined using your referral link!\n"
                f"You'll earn $0.10 when they purchase premium.\n\n"
                f"👥 Keep sharing to earn more!"
            )
        except:
            pass  # Referrer might have blocked the bot
    else:
        # Already referred, show normal start
        from bot.plugins.start_handler import start_command
        await start_command(client, message)

@Client.on_callback_query(filters.regex("^referral_"))
async def referral_callbacks(client: Client, query: CallbackQuery):
    """Handle referral program callbacks"""
    user_id = query.from_user.id
    callback_data = query.data
    
    if callback_data == "referral_detailed_stats":
        await show_detailed_referral_stats(client, query)
    elif callback_data == "referral_leaderboard":
        await show_referral_leaderboard(client, query)
    elif callback_data == "referral_share_link":
        await show_share_options(client, query)
    elif callback_data == "referral_tips":
        await show_referral_tips(client, query)

async def show_detailed_referral_stats(client: Client, query: CallbackQuery):
    """Show detailed referral statistics"""
    user_id = query.from_user.id
    
    stats = await get_referral_stats(user_id)
    if not stats:
        await query.answer("❌ No referral data found!", show_alert=True)
        return
    
    text = f"📊 **Detailed Referral Stats**\n\n"
    text += f"🔗 **Your Code:** `{stats['referral_code']}`\n\n"
    text += f"📈 **Performance:**\n"
    text += f"• Total Referrals: {stats['total_referrals']}\n"
    text += f"• Total Earnings: ${stats['total_earnings']:.2f}\n"
    text += f"• Pending Rewards: {stats['pending_rewards']}\n"
    text += f"• Paid Rewards: {stats['paid_rewards']}\n\n"
    
    if stats['referral_history']:
        text += f"📋 **Recent Referrals:**\n"
        for i, ref in enumerate(stats['referral_history'][-5:], 1):
            status = "💰 Rewarded" if ref['reward_paid'] else "⏳ Pending"
            date = ref['referred_at'].strftime('%m/%d')
            text += f"{i}. {date} - {status}\n"
    
    text += f"\n💡 **Tips:**\n"
    text += f"• Share your link on social media\n"
    text += f"• Explain the benefits of clone bots\n"
    text += f"• Help new users understand premium features"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Referral", callback_data="show_referral_main")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

async def show_referral_leaderboard(client: Client, query: CallbackQuery):
    """Show referral program leaderboard"""
    top_referrers = await get_top_referrers(10)
    
    text = f"🏆 **Referral Leaderboard**\n\n"
    
    if not top_referrers:
        text += "🔍 **No referrers yet!**\n\n"
        text += "Be the first to start referring and climb the leaderboard!"
    else:
        for i, referrer in enumerate(top_referrers, 1):
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{emoji} ${referrer['total_earnings']:.2f} • {referrer['total_referrals']} refs\n"
    
    text += f"\n💡 **Compete and Earn:**\n"
    text += f"• More referrals = More earnings\n"
    text += f"• Help others discover clone bots\n"
    text += f"• Build your passive income!"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Referral", callback_data="show_referral_main")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

async def show_share_options(client: Client, query: CallbackQuery):
    """Show referral link sharing options"""
    user_id = query.from_user.id
    
    referral_code = await get_referral_code(user_id)
    if not referral_code:
        await query.answer("❌ Error loading referral code!", show_alert=True)
        return
    
    bot_username = client.me.username
    referral_url = f"https://t.me/{bot_username}?start=ref_{referral_code}"
    
    text = f"📱 **Share Your Referral Link**\n\n"
    text += f"🔗 **Your Link:**\n"
    text += f"`{referral_url}`\n\n"
    text += f"📋 **Ready-to-use Messages:**\n\n"
    text += f"**Message 1:**\n"
    text += f"🤖 Check out this awesome Telegram bot that creates personal file-sharing bots! Get your own clone bot: {referral_url}\n\n"
    text += f"**Message 2:**\n"
    text += f"💾 Want your own file storage bot? This service creates personal Telegram bots for file sharing. Try it: {referral_url}\n\n"
    text += f"**Message 3:**\n"
    text += f"🚀 I'm using this bot creator service - you can make your own Telegram bot in minutes! Check it out: {referral_url}"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Copy Link", callback_data=f"copy_referral:{referral_code}")],
        [InlineKeyboardButton("🔙 Back to Referral", callback_data="show_referral_main")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

async def show_referral_tips(client: Client, query: CallbackQuery):
    """Show referral program tips and strategies"""
    text = f"💡 **Referral Success Tips**\n\n"
    text += f"🎯 **Best Practices:**\n\n"
    text += f"1. **Target the Right Audience**\n"
    text += f"   • Tech enthusiasts\n"
    text += f"   • Content creators\n"
    text += f"   • File sharing communities\n\n"
    text += f"2. **Explain the Value**\n"
    text += f"   • Personal file storage bot\n"
    text += f"   • Secure file sharing\n"
    text += f"   • Easy bot creation process\n\n"
    text += f"3. **Where to Share**\n"
    text += f"   • Telegram groups/channels\n"
    text += f"   • Discord servers\n"
    text += f"   • Reddit communities\n"
    text += f"   • Social media platforms\n\n"
    text += f"4. **Provide Support**\n"
    text += f"   • Help new users get started\n"
    text += f"   • Answer questions about features\n"
    text += f"   • Guide them through setup\n\n"
    text += f"💰 **Earning Potential:**\n"
    text += f"• 10 referrals → $1.00\n"
    text += f"• 50 referrals → $5.00\n"
    text += f"• 100 referrals → $10.00"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Referral", callback_data="show_referral_main")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^show_referral_main$"))
async def show_referral_main(client: Client, query: CallbackQuery):
    """Show main referral program page"""
    # Redirect to referral command
    user_id = query.from_user.id
    
    # Create a fake message object
    class FakeMessage:
        def __init__(self, query):
            self.from_user = query.from_user
            self.chat = query.message.chat
        async def reply_text(self, text, reply_markup=None):
            await query.edit_message_text(text, reply_markup=reply_markup)
    
    fake_message = FakeMessage(query)
    await referral_command(client, fake_message)

@Client.on_callback_query(filters.regex("^copy_referral:"))
async def copy_referral_callback(client: Client, query: CallbackQuery):
    """Handle copy referral link callback"""
    referral_code = query.data.split(":")[1]
    bot_username = client.me.username
    referral_url = f"https://t.me/{bot_username}?start=ref_{referral_code}"
    
    await query.answer(f"📋 Referral link copied!\n{referral_url}", show_alert=True)
