
import uvloop
import asyncio
import logging
from pyrogram import idle
from bot import Bot
from clone_manager import clone_manager

logger = logging.getLogger(__name__)

uvloop.install()

async def main():
    """Main function for Mother Bot + Clone System"""
    print("🚀 Starting Mother Bot + Clone System...")
    
    # Start the mother bot
    print("📡 Initializing Mother Bot...")
    app = Bot()
    await app.start()
    
    # Get bot info
    me = await app.get_me()
    print(f"✅ Mother Bot @{me.username} started successfully!")
    
    # Initialize databases
    try:
        from bot.database.subscription_db import init_pricing_tiers
        from bot.database.clone_db import set_global_force_channels
        
        await init_pricing_tiers()
        print("✅ Database initialized")
        
        # Set default global settings if not exist
        from bot.database.clone_db import get_global_about, set_global_about
        global_about = await get_global_about()
        if not global_about:
            default_about = (
                "🤖 **About This Bot**\n\n"
                "This bot is powered by the Mother Bot System - "
                "an advanced file-sharing platform with clone creation capabilities.\n\n"
                "✨ **Features:**\n"
                "• Fast & reliable file sharing\n"
                "• Advanced search capabilities\n"
                "• Token verification system\n"
                "• Premium subscriptions\n"
                "• Clone bot creation\n\n"
                "🌟 **Want your own bot?**\n"
                "Contact the admin to create your personalized clone!\n\n"
                "🤖 **Made by Mother Bot System**\n"
                "Professional bot hosting & management solutions."
            )
            await set_global_about(default_about)
            print("✅ Default global about page set")
            
    except Exception as e:
        print(f"⚠️ Database initialization error: {e}")
    
    # Initialize clone manager
    try:
        print("🔄 Starting Clone Manager...")
        await clone_manager.start_all_clones()
        print("✅ Clone manager initialized")
        
        # Start subscription monitoring in background
        print("⏱️ Starting subscription monitoring...")
        asyncio.create_task(clone_manager.check_subscriptions())
        print("✅ Subscription monitoring started")
        
    except Exception as e:
        print(f"⚠️ Clone manager error: {e}")
    
    # Start subscription monitoring for mother bot
    try:
        from bot.utils.subscription_checker import subscription_checker
        asyncio.create_task(subscription_checker.start_monitoring())
        print("✅ Mother Bot subscription monitoring started")
    except Exception as e:
        print(f"⚠️ Mother Bot subscription monitoring error: {e}")
    
    print("\n" + "="*60)
    print("🎉 MOTHER BOT + CLONE SYSTEM READY!")
    print("="*60)
    print(f"🤖 Mother Bot: @{me.username}")
    print(f"📊 Running Clones: {len(clone_manager.get_running_clones())}")
    print(f"🎛️ Admin Panel: /motheradmin")
    print(f"🆕 Create Clone: /createclone")
    print("="*60)
    
    # Keep the application running
    await idle()
    
    # Graceful shutdown
    print("\n🛑 Shutting down Mother Bot System...")
    
    # Stop all clones
    for bot_id in list(clone_manager.instances.keys()):
        await clone_manager.stop_clone(bot_id)
    
    # Stop mother bot
    await app.stop()
    print("✅ Mother Bot System shut down complete.")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Received interrupt signal. Shutting down...")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        logging.exception("Fatal error occurred")
