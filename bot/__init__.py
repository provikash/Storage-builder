import sys, asyncio
from datetime import datetime
from pyrogram import Client
from info import Config
from bot.logging import LOGGER
from bot.utils import schedule_manager
from bot.utils.clone_config_loader import clone_config_loader

ascii_art = """ 
██████████████████████████████████▀███████
█─▄▄▄▄█─▄─▄─█─▄▄─█▄─▄▄▀██▀▄─██─▄▄▄▄█▄─▄▄─█
█▄▄▄▄─███─███─██─██─▄─▄██─▀─██─██▄─██─▄█▀█
▀▄▄▄▄▄▀▀▄▄▄▀▀▄▄▄▄▀▄▄▀▄▄▀▄▄▀▄▄▀▄▄▄▄▄▀▄▄▄▄▄▀
██████████████████
█▄─▄─▀█─▄▄─█─▄─▄─█
██─▄─▀█─██─███─███
▀▄▄▄▄▀▀▄▄▄▄▀▀▄▄▄▀▀
██████████████████████████████████████████
█▄─▄─▀█▄─██─▄█▄─▄█▄─▄███▄─▄▄▀█▄─▄▄─█▄─▄▄▀█
██─▄─▀██─██─███─███─██▀██─██─██─▄█▀██─▄─▄█
▀▄▄▄▄▀▀▀▄▄▄▄▀▀▄▄▄▀▄▄▄▄▄▀▄▄▄▄▀▀▄▄▄▄▄▀▄▄▀▄▄▀"""

class Bot(Client):
    def __init__(self, bot_token=None, clone_config=None):
        # Use provided token or default to mother bot token
        token = bot_token or Config.BOT_TOKEN

        super().__init__(
            name="bot" if not bot_token else f"clone_{token.split(':')[0]}",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=token,
            workers=100,
            plugins={"root": "bot.plugins"},
            sleep_threshold=5,
        )

        # Set bot configuration
        self.is_clone = bool(bot_token)
        self.clone_config = clone_config
        self.bot_token = token
        self.log = LOGGER
        self.username = None

    async def start(self):
        await super().start()
        me = await self.get_me()
        self.username = me.username
        self.mention = me.mention
        self.uptime = datetime.now()
        self.channel_info = {}

        # Load clone configuration if it's a clone bot
        if self.is_clone:
            await clone_config_loader.load_config(self)
            self.log(__name__).info(f"Clone Bot Started: {self.username}")
        else:
            # Load mother bot configurations
            self.log(__name__).info("Mother Bot Started")
            # Load force subscription channel info for mother bot
            for channel_id in Config.FORCE_SUB_CHANNEL:
                try:
                    chat = await self.get_chat(channel_id)
                    title = chat.title
                    link = chat.invite_link

                    if not link:
                        link = await self.export_chat_invite_link(channel_id)

                    self.channel_info[channel_id] = {"title": title, "invite_link": link}
                    print(f"✅ Loaded force channel info: {title} - {link}")
                except Exception as e:
                    print(f"❌ Error loading force channel {channel_id}: {e}")

            # Load request channel info for mother bot
            request_channels = getattr(Config, 'REQUEST_CHANNEL', [])
            for channel_id in request_channels:
                try:
                    chat = await self.get_chat(channel_id)
                    title = chat.title

                    self.channel_info[channel_id] = {"title": title, "invite_link": None}
                    print(f"✅ Loaded request channel info: {title}")
                except Exception as e:
                    print(f"❌ Error loading request channel {channel_id}: {e}")


            # Initialize database channel for mother bot
            try:
                db_channel = await self.get_chat(Config.CHANNEL_ID)
                self.db_channel = db_channel
                test = await self.send_message(chat_id=db_channel.id, text="Test Message")
                await test.delete()
            except Exception as e:
                self.log(__name__).warning(e)
                self.log(__name__).warning(f"Make Sure bot is Admin in DB Channel, and Double check the CHANNEL_ID Value, Current Value {Config.CHANNEL_ID}")
                self.log(__name__).info("\nBot Stopped. Join https://t.me/ps_discuss for support")
                sys.exit()

        print(ascii_art)
        await asyncio.sleep(1.5)
        self.log(__name__).info(f"Bot Running..!\n\nCreated by \nhttps://t.me/ps_updates")
        print("""Welcome to Mother Bot - File Sharing System""")

        await schedule_manager.start()
        asyncio.create_task(schedule_manager.recover_pending_tasks())

        if Config.WEB_MODE:
            from web import start_webserver
            asyncio.create_task(start_webserver(self, Config.PORT))

    async def stop(self, *args):
        await super().stop()
        self.log(__name__).info("Bot stopped.")