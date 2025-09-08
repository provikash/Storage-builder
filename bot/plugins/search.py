# Updated random files retrieval to use clone-specific database and handle clone IDs.
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from bot.database import get_random_files, get_popular_files, get_recent_files, get_index_stats, increment_access_count, is_premium_user
from bot.utils import encode, get_readable_file_size, handle_force_sub
from bot.utils.command_verification import check_command_limit, use_command
from bot.utils.token_verification import TokenVerificationManager
from info import Config
import asyncio
import traceback
from datetime import datetime, timedelta
from bot.database.mongo_db import collection

# --- Feature Checking Function ---
async def check_feature_enabled(client: Client, feature_name: str) -> bool:
    """Check if a feature is enabled for the current bot"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)

        # Check if this is a clone bot first
        is_clone_bot = (
            bot_token != Config.BOT_TOKEN or
            hasattr(client, 'is_clone') and client.is_clone or
            hasattr(client, 'clone_config') and client.clone_config or
            hasattr(client, 'clone_data')
        )

        # Mother bot - features are disabled (redirect to clone creation)
        if not is_clone_bot and bot_token == Config.BOT_TOKEN:
            return False

        # For clone bots, check the database
        from bot.database.clone_db import get_clone_by_bot_token
        clone_data = await get_clone_by_bot_token(bot_token)

        if not clone_data:
            print(f"WARNING: Clone data not found for bot token {bot_token}. Assuming feature '{feature_name}' is enabled for clone.")
            return True  # Default to enabled for clone bots

        # Return the enabled status of the feature, default to True if not specified
        return clone_data.get(f'{feature_name}_mode', True)
    except Exception as e:
        print(f"Error checking feature {feature_name}: {e}")
        return True  # Default to enabled on error for clone bots

# --- Command Handlers ---

@Client.on_message(filters.command("rand") & filters.private)
async def random_command(client: Client, message: Message):
    """Handle random command to show 5 random files"""
    try:
        print(f"DEBUG: /rand command received from user {message.from_user.id}")

        # Check force subscription first
        if await handle_force_sub(client, message):
            return

        # Check if the random feature is enabled
        if not await check_feature_enabled(client, 'random'):
            await message.reply_text("❌ Random files feature is currently disabled by the admin.")
            return

        user_id = message.from_user.id

        # Check command limit and use command if allowed
        if not await use_command(user_id, client):
            needs_verification, remaining = await check_command_limit(user_id, client)

            # Get verification mode for appropriate message
            token_settings = await TokenVerificationManager.get_clone_token_settings(client)
            verification_mode = token_settings.get('verification_mode', 'command_limit')

            # Create verification button
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ])

            if verification_mode == 'time_based':
                duration = token_settings.get('time_duration', 24)
                message_text = (
                    f"⚠️ **Verification Required!**\n\n"
                    f"🕐 **Time-Based Access:** Get {duration} hours of unlimited commands!\n\n"
                    f"🔓 **Get instant access by:**\n"
                    f"• Getting a verification token ({duration}h unlimited access)\n"
                    f"• Upgrading to Premium (permanent unlimited access)\n\n"
                    f"💡 Premium users get unlimited access without verification!"
                )
            else:
                command_limit = token_settings.get('command_limit', 3)
                message_text = (
                    f"⚠️ **Command Limit Reached!**\n\n"
                    f"You've used all your free commands.\n\n"
                    f"🔓 **Get instant access by:**\n"
                    f"• Getting a verification token ({command_limit} more commands)\n"
                    f"• Upgrading to Premium (unlimited commands)\n\n"
                    f"💡 Premium users get unlimited access without verification!"
                )

            await message.reply_text(message_text, reply_markup=buttons)
            return
        await handle_random_files(client, message)
    except Exception as cmd_error:
        print(f"ERROR: /rand command failed: {cmd_error}")
        try:
            await message.reply_text(f"❌ Command failed: {str(cmd_error)}")
        except Exception as reply_error:
            print(f"ERROR: Could not send error reply: {reply_error}")

@Client.on_message(filters.private & filters.text & filters.regex(r"^🎲 Random$"))
async def keyboard_random_handler(client: Client, message: Message):
    """Handle Random button press from custom keyboard"""
    try:
        print(f"DEBUG: Keyboard random handler triggered by user {message.from_user.id}")

        # Check force subscription first
        if await handle_force_sub(client, message):
            return

        # Check if the random feature is enabled
        if not await check_feature_enabled(client, 'random'):
            await message.reply_text("❌ Random files feature is currently disabled by the admin.")
            return

        user_id = message.from_user.id

        # Check command limit first
        needs_verification, remaining = await check_command_limit(user_id, client)

        # Only show verification dialog if user actually needs verification AND has no remaining commands
        if needs_verification and remaining <= 0:
            # Get verification mode for appropriate message
            token_settings = await TokenVerificationManager.get_clone_token_settings(client)
            verification_mode = token_settings.get('verification_mode', 'command_limit')

            # Create verification button
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ])

            if verification_mode == 'time_based':
                duration = token_settings.get('time_duration', 24)
                message_text = (
                    f"⚠️ **Verification Required!**\n\n"
                    f"🕐 **Time-Based Access:** Get {duration} hours of unlimited commands!\n\n"
                    f"🔓 **Get instant access by:**\n"
                    f"• Getting a verification token ({duration}h unlimited access)\n"
                    f"• Upgrading to Premium (permanent unlimited access)\n\n"
                    f"💡 Premium users get unlimited access without verification!"
                )
            else:
                command_limit = token_settings.get('command_limit', 3)
                message_text = (
                    f"⚠️ **Command Limit Reached!**\n\n"
                    f"You've used all your free commands.\n\n"
                    f"🔓 **Get instant access by:**\n"
                    f"• Getting a verification token ({command_limit} more commands)\n"
                    f"• Upgrading to Premium (unlimited commands)\n\n"
                    f"💡 Premium users get unlimited access without verification!"
                )

            await message.reply_text(message_text, reply_markup=buttons)
            return

        # Try to use command (this will handle admin/premium logic internally)
        if not await use_command(user_id, client):
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ])
            await message.reply_text(
                "🔐 **Command Limit Reached!**\n\nYou've used all your free commands. Please verify to get 3 more commands or upgrade to Premium for unlimited access!",
                reply_markup=buttons
            )
            return

        await handle_random_files(client, message, is_callback=False, skip_command_check=True)

    except Exception as e:
        print(f"ERROR in keyboard_random_handler: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        await message.reply_text("❌ An error occurred. Please try again.")

@Client.on_message(filters.private & filters.text & filters.regex(r"^🆕 Recent Added$"))
async def keyboard_recent_handler(client: Client, message: Message):
    """Handle Recent Added button press from custom keyboard"""
    try:
        print(f"DEBUG: Keyboard recent handler triggered by user {message.from_user.id}")

        # Check force subscription first
        if await handle_force_sub(client, message):
            return

        # Check if the recent feature is enabled
        if not await check_feature_enabled(client, 'recent'):
            await message.reply_text("❌ Recent files feature is currently disabled by the admin.")
            return

        user_id = message.from_user.id

        # Check command limit first
        needs_verification, remaining = await check_command_limit(user_id, client)

        # Only show verification dialog if user actually needs verification AND has no remaining commands
        if needs_verification and remaining <= 0:
            # Get verification mode for appropriate message
            token_settings = await TokenVerificationManager.get_clone_token_settings(client)
            verification_mode = token_settings.get('verification_mode', 'command_limit')

            # Create verification button
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ])

            if verification_mode == 'time_based':
                duration = token_settings.get('time_duration', 24)
                message_text = (
                    f"⚠️ **Verification Required!**\n\n"
                    f"🕐 **Time-Based Access:** Get {duration} hours of unlimited commands!\n\n"
                    f"🔓 **Get instant access by:**\n"
                    f"• Getting a verification token ({duration}h unlimited access)\n"
                    f"• Upgrading to Premium (permanent unlimited access)\n\n"
                    f"💡 Premium users get unlimited access without verification!"
                )
            else:
                command_limit = token_settings.get('command_limit', 3)
                message_text = (
                    f"⚠️ **Command Limit Reached!**\n\n"
                    f"You've used all your free commands.\n\n"
                    f"🔓 **Get instant access by:**\n"
                    f"• Getting a verification token ({command_limit} more commands)\n"
                    f"• Upgrading to Premium (unlimited commands)\n\n"
                    f"💡 Premium users get unlimited access without verification!"
                )

            await message.reply_text(message_text, reply_markup=buttons)
            return

        # Try to use command (this will handle admin/premium logic internally)
        if not await use_command(user_id, client):
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ])
            await message.reply_text(
                "🔐 **Command Limit Reached!**\n\nYou've used all your free commands. Please verify to get 3 more commands or upgrade to Premium for unlimited access!",
                reply_markup=buttons
            )
            return

        await handle_recent_files_direct(client, message, is_callback=False)

    except Exception as e:
        print(f"ERROR in keyboard_recent_handler: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        await message.reply_text("❌ An error occurred. Please try again.")

@Client.on_message(filters.private & filters.text & filters.regex(r"^🔥 Most Popular$"))
async def keyboard_popular_handler(client: Client, message: Message):
    """Handle Most Popular button press from custom keyboard"""
    try:
        print(f"DEBUG: Keyboard popular handler triggered by user {message.from_user.id}")

        # Check force subscription first
        if await handle_force_sub(client, message):
            return

        # Check if the popular feature is enabled
        if not await check_feature_enabled(client, 'popular'):
            await message.reply_text("❌ Most popular files feature is currently disabled by the admin.")
            return

        user_id = message.from_user.id

        # Check command limit first
        needs_verification, remaining = await check_command_limit(user_id, client)

        # Only show verification dialog if user actually needs verification AND has no remaining commands
        if needs_verification and remaining <= 0:
            # Get verification mode for appropriate message
            token_settings = await TokenVerificationManager.get_clone_token_settings(client)
            verification_mode = token_settings.get('verification_mode', 'command_limit')

            # Create verification button
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ])

            if verification_mode == 'time_based':
                duration = token_settings.get('time_duration', 24)
                message_text = (
                    f"⚠️ **Verification Required!**\n\n"
                    f"🕐 **Time-Based Access:** Get {duration} hours of unlimited commands!\n\n"
                    f"🔓 **Get instant access by:**\n"
                    f"• Getting a verification token ({duration}h unlimited access)\n"
                    f"• Upgrading to Premium (permanent unlimited access)\n\n"
                    f"💡 Premium users get unlimited access without verification!"
                )
            else:
                command_limit = token_settings.get('command_limit', 3)
                message_text = (
                    f"⚠️ **Command Limit Reached!**\n\n"
                    f"You've used all your free commands.\n\n"
                    f"🔓 **Get instant access by:**\n"
                    f"• Getting a verification token ({command_limit} more commands)\n"
                    f"• Upgrading to Premium (unlimited commands)\n\n"
                    f"💡 Premium users get unlimited access without verification!"
                )

            await message.reply_text(message_text, reply_markup=buttons)
            return

        # Try to use command (this will handle admin/premium logic internally)
        if not await use_command(user_id, client):
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ])
            await message.reply_text(
                "🔐 **Command Limit Reached!**\n\nYou've used all your free commands. Please verify to get 3 more commands or upgrade to Premium for unlimited access!",
                reply_markup=buttons
            )
            return

        # Call handle_popular_files_direct directly
        await handle_popular_files_direct(client, message, is_callback=False)

    except Exception as e:
        print(f"ERROR in keyboard_popular_handler: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        await message.reply_text("❌ An error occurred. Please try again.")

@Client.on_message(filters.private & filters.text & filters.regex(r"^🎲 Random Files$"))
async def keyboard_random_handler_sync(client: Client, message: Message):
    """Handle Random Files button press from custom keyboard - synchronized with inline button"""
    try:
        print(f"DEBUG: Keyboard Random Files handler triggered by user {message.from_user.id}")

        # Check force subscription first
        if await handle_force_sub(client, message):
            return

        # Check if the random feature is enabled
        if not await check_feature_enabled(client, 'random'):
            await message.reply_text("❌ Random files feature is currently disabled by the admin.")
            return

        user_id = message.from_user.id

        # First check if verification is needed
        needs_verification, remaining = await check_command_limit(user_id, client)

        if needs_verification:
            # Get verification mode for appropriate message
            token_settings = await TokenVerificationManager.get_clone_token_settings(client)
            verification_mode = token_settings.get('verification_mode', 'command_limit')

            buttons = [
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ]

            if verification_mode == 'time_based':
                duration = token_settings.get('time_duration', 24)
                message_text = (
                    f"⚠️ **Verification Required!**\n\n"
                    f"🕐 **Time-Based Access:** Get {duration} hours of unlimited commands!\n\n"
                    f"🔓 **Get instant access by:**\n"
                    f"• Getting a verification token ({duration}h unlimited access)\n"
                    f"• Upgrading to Premium (permanent unlimited access)\n\n"
                    f"💡 Premium users get unlimited access without verification!"
                )
            else:
                command_limit = token_settings.get('command_limit', 3)
                message_text = (
                    f"⚠️ **Verification Required!**\n\n"
                    f"You need to verify your account to continue. Get a verification token to access {command_limit} more commands!"
                )

            await message.reply_text(message_text, reply_markup=InlineKeyboardMarkup(buttons))
            return

        # Try to use command
        if not await use_command(user_id, client):
            buttons = [
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ]
            await message.reply_text(
                "🔐 **Command Limit Reached!**\n\nYou've used all your free commands. Please verify to get 3 more commands or upgrade to Premium for unlimited access!",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            return

        # Execute random files function - same as callback
        await handle_random_files(client, message, is_callback=False, skip_command_check=True)

    except Exception as e:
        print(f"ERROR in keyboard_random_handler_sync: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        await message.reply_text("❌ An error occurred. Please try again.")

@Client.on_message(filters.private & filters.text & filters.regex(r"^💎 Premium Plans$"))
async def keyboard_premium_handler(client: Client, message: Message):
    """Handle Buy Premium button press from custom keyboard"""
    try:
        # Check force subscription first
        if await handle_force_sub(client, message):
            return

        user_id = message.from_user.id

        # Check if user is already premium
        if await is_premium_user(user_id):
            return await message.reply_text("✨ You're already a Premium Member!")

        # Create a mock callback to reuse existing premium function
        from pyrogram.types import CallbackQuery

        class MockCallback:
            def __init__(self, message):
                self.message = message
                self.from_user = message.from_user
                self.data = "show_premium_plans"

            async def answer(self, text="", show_alert=False):
                pass

            async def edit_message_text(self, text, reply_markup=None):
                await self.message.reply_text(text, reply_markup=reply_markup)

        mock_callback = MockCallback(message)
        from bot.plugins.callback import show_premium_callback
        await show_premium_callback(client, mock_callback)

    except Exception as e:
        print(f"ERROR in keyboard_premium_handler: {e}")
        await message.reply_text("❌ An error occurred. Please try again.")

@Client.on_callback_query(filters.regex(r"^rand_"))
async def random_callback(client: Client, callback_query: CallbackQuery):
    """Handle random-related callbacks"""
    try:
        print(f"DEBUG: Random callback received: {callback_query.data} from user {callback_query.from_user.id}")

        # Check force subscription first
        if await handle_force_sub(client, callback_query.message):
            return

        data = callback_query.data.split("_", 1)

        if len(data) < 2:
            print(f"ERROR: Invalid callback data format: {callback_query.data}")
            await callback_query.answer("❌ Invalid action", show_alert=True)
            return

        action = data[1]
        print(f"DEBUG: Executing action: {action}")

        if action == "new":
            # Check if the random feature is enabled before calling handler
            if not await check_feature_enabled(client, 'random'):
                await callback_query.answer("❌ Random files feature is currently disabled by the admin.", show_alert=True)
                return
            await handle_random_files(client, callback_query.message, is_callback=True)

        elif action == "popular":
            # Check if the popular feature is enabled before calling handler
            if not await check_feature_enabled(client, 'popular'):
                await callback_query.answer("❌ Most popular files feature is currently disabled by the admin.", show_alert=True)
                return
            await show_popular_files(client, callback_query)

        elif action == "recent":
            # Check if the recent feature is enabled before calling handler
            if not await check_feature_enabled(client, 'recent'):
                await callback_query.answer("❌ Recent files feature is currently disabled by the admin.", show_alert=True)
                return
            await show_recent_files(client, callback_query)

        elif action == "stats":
            await show_index_stats(client, callback_query)

        else:
            print(f"WARNING: Unknown action: {action}")
            await callback_query.answer("❌ Unknown action", show_alert=True)

        # Acknowledge the callback
        try:
            await callback_query.answer()
        except Exception as ack_error:
            print(f"WARNING: Could not acknowledge callback: {ack_error}")

    except Exception as callback_error:
        print(f"ERROR: Callback handler failed: {callback_error}")
        try:
            await callback_query.answer(f"❌ Error: {str(callback_error)}", show_alert=True)
        except Exception as answer_error:
            print(f"ERROR: Could not send callback answer: {answer_error}")

async def handle_random_files(client: Client, message, is_callback: bool = False, skip_command_check: bool = False):
    """Get and display 5 random files using proper MongoDB to Telegram retrieval process"""
    loading_msg = None

    try:
        # Determine clone ID to use the correct database
        clone_id = getattr(client, 'clone_id', None)
        if clone_id is None:
            # If not a clone bot or clone_id not set, try to get from token
            bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
            if bot_token != Config.BOT_TOKEN:
                from bot.database.clone_db import get_clone_by_bot_token
                clone_data = await get_clone_by_bot_token(bot_token)
                if clone_data:
                    clone_id = clone_data.get('id')

        if clone_id is None:
            await message.reply_text("❌ Error: Cannot determine clone ID. Please ensure this is a valid clone bot.")
            return

        # Initialize loading message
        if is_callback:
            loading_msg = await message.edit_text("🎲 Getting random files...")
        else:
            loading_msg = await message.reply_text("🎲 Getting random files...")

        print(f"DEBUG: Starting random files retrieval for clone ID: {clone_id}")

        # Step 1: Query MongoDB for file metadata
        try:
            # Updated to use clone_id for database selection
            results = await get_random_files(limit=15, clone_id=clone_id)  # Get more to account for invalid files
            print(f"DEBUG: Retrieved {len(results)} files from database for clone {clone_id}")
        except Exception as db_error:
            error_msg = f"❌ Database query failed: {str(db_error)}"
            print(f"ERROR: MongoDB query failed for clone {clone_id}: {db_error}")
            await loading_msg.edit_text(error_msg)
            return

        if not results:
            text = "❌ No files found in database."
            print(f"DEBUG: No files found in database for clone {clone_id}")
            await loading_msg.edit_text(text)
            return

        try:
            await loading_msg.edit_text(f"📁 Processing {len(results)} random files...")
        except Exception as msg_error:
            print(f"WARNING: Failed to update loading message: {msg_error}")

        # Step 2: Retrieve files from Telegram via file_id and send to user
        sent_count = 0
        target_count = 5  # Target number of files to send
        errors_encountered = []

        for idx, file_data in enumerate(results):
            if sent_count >= target_count:
                print(f"DEBUG: Reached target count of {target_count} files")
                break

            print(f"DEBUG: Processing file {idx + 1}/{len(results)}")

            try:
                # Extract metadata from MongoDB document with validation
                if not isinstance(file_data, dict):
                    print(f"ERROR: Invalid file_data type: {type(file_data)}")
                    errors_encountered.append(f"Invalid data structure for file {idx + 1}")
                    continue

                file_id = str(file_data.get('_id', ''))
                file_name = file_data.get('file_name', 'Unknown File')
                file_type = file_data.get('file_type', 'unknown')
                file_size = file_data.get('file_size', 0)

                if not file_id:
                    print(f"ERROR: No file_id found for file: {file_name}")
                    errors_encountered.append(f"Missing file_id for {file_name}")
                    continue

                print(f"DEBUG: Processing file: {file_name} with ID: {file_id}, Type: {file_type}")

                # Step 3: Parse file_id to extract message_id
                message_id = None
                try:
                    if '_' in file_id:
                        # Format: "chat_id_message_id" (e.g., "-1002315371279_1767")
                        parts = file_id.split('_')
                        if len(parts) >= 2:
                            message_id = int(parts[-1])  # Get the last part as message ID
                            print(f"DEBUG: Extracted message_id {message_id} from composite ID: {file_id}")
                        else:
                            print(f"ERROR: Invalid composite file_id format: {file_id}")
                            errors_encountered.append(f"Invalid ID format: {file_id}")
                            continue
                    else:
                        # Format: just "message_id"
                        message_id = int(file_id)
                        print(f"DEBUG: Using direct message_id: {message_id}")

                except (ValueError, IndexError) as parse_error:
                    print(f"ERROR: Failed to parse message ID from {file_id}: {parse_error}")
                    errors_encountered.append(f"Parse error for {file_id}: {str(parse_error)}")
                    continue

                if not message_id or message_id <= 0:
                    print(f"ERROR: Invalid message_id {message_id} for file: {file_id}")
                    errors_encountered.append(f"Invalid message_id {message_id}")
                    continue

                # Step 4: Retrieve file from Telegram using the database channel
                try:
                    print(f"DEBUG: Fetching message {message_id} from channel {Config.INDEX_CHANNEL_ID}")

                    # Validate channel access first
                    try:
                        # Check if bot has access to the channel
                        await client.get_chat(Config.INDEX_CHANNEL_ID)
                    except Exception as channel_error:
                        print(f"ERROR: Cannot access channel {Config.INDEX_CHANNEL_ID}: {channel_error}")
                        errors_encountered.append(f"Channel access denied: {Config.INDEX_CHANNEL_ID}")
                        continue

                    # Get the message from the index channel (where files are stored)
                    db_message = await client.get_messages(Config.INDEX_CHANNEL_ID, message_id)

                    if not db_message:
                        print(f"ERROR: Message {message_id} returned None")
                        errors_encountered.append(f"Message {message_id} not found")
                        continue

                    if db_message.empty:
                        print(f"ERROR: Message {message_id} is empty")
                        errors_encountered.append(f"Message {message_id} is empty")
                        continue

                    # Validate the message has media
                    if not db_message.media:
                        print(f"ERROR: Message {message_id} has no media")
                        errors_encountered.append(f"Message {message_id} has no media")
                        continue

                    print(f"DEBUG: Successfully retrieved message {message_id} with media type: {type(db_message.media)}")

                except Exception as telegram_get_error:
                    print(f"ERROR: Telegram get_messages failed for message {message_id}: {telegram_get_error}")
                    errors_encountered.append(f"Get message {message_id}: {str(telegram_get_error)}")
                    continue

                # Step 5: Send the file to user without caption/title but with custom keyboard
                try:
                    print(f"DEBUG: Sending media from message {message_id} to user {message.chat.id}")

                    # Create custom keyboard with the requested buttons
                    custom_keyboard = ReplyKeyboardMarkup([
                        [
                            KeyboardButton("🎲 Random"),
                            KeyboardButton("🆕 Recent Added")
                        ],
                        [
                            KeyboardButton("💎 Buy Premium"),
                            KeyboardButton("🔥 Most Popular")
                        ]
                    ], resize_keyboard=True, one_time_keyboard=False)

                    # Send media based on type without any caption but with custom keyboard
                    copied_msg = None
                    if db_message.photo:
                        copied_msg = await client.send_photo(
                            chat_id=message.chat.id,
                            photo=db_message.photo.file_id,
                            reply_markup=custom_keyboard,
                            protect_content=Config.PROTECT_CONTENT
                        )
                    elif db_message.video:
                        copied_msg = await client.send_video(
                            chat_id=message.chat.id,
                            video=db_message.video.file_id,
                            reply_markup=custom_keyboard,
                            protect_content=Config.PROTECT_CONTENT
                        )
                    elif db_message.document:
                        copied_msg = await client.send_document(
                            chat_id=message.chat.id,
                            document=db_message.document.file_id,
                            reply_markup=custom_keyboard,
                            protect_content=Config.PROTECT_CONTENT
                        )
                    elif db_message.audio:
                        copied_msg = await client.send_audio(
                            chat_id=message.chat.id,
                            audio=db_message.audio.file_id,
                            reply_markup=custom_keyboard,
                            protect_content=Config.PROTECT_CONTENT
                        )
                    elif db_message.voice:
                        copied_msg = await client.send_voice(
                            chat_id=message.chat.id,
                            voice=db_message.voice.file_id,
                            reply_markup=custom_keyboard,
                            protect_content=Config.PROTECT_CONTENT
                        )
                    elif db_message.animation:
                        copied_msg = await client.send_animation(
                            chat_id=message.chat.id,
                            animation=db_message.animation.file_id,
                            reply_markup=custom_keyboard,
                            protect_content=Config.PROTECT_CONTENT
                        )
                    else:
                        # Fallback to copy method without caption but with custom keyboard
                        copied_msg = await db_message.copy(
                            chat_id=message.chat.id,
                            reply_markup=custom_keyboard,
                            protect_content=Config.PROTECT_CONTENT
                        )

                    if copied_msg:
                        sent_count += 1
                        print(f"SUCCESS: Sent file #{sent_count}: {file_name}")

                        # Increment access count in database
                        try:
                            await increment_access_count(file_id)
                            print(f"DEBUG: Incremented access count for {file_id}")
                        except Exception as count_error:
                            print(f"WARNING: Failed to increment access count for {file_id}: {count_error}")

                        # Small delay to avoid flooding
                        await asyncio.sleep(1.0)
                    else:
                        print(f"ERROR: Send operation returned None for message {message_id}")
                        errors_encountered.append(f"Send failed for message {message_id}")

                except Exception as send_error:
                    print(f"ERROR: Failed to send message {message_id}: {send_error}")
                    errors_encountered.append(f"Send error for {message_id}: {str(send_error)}")
                    continue

            except Exception as processing_error:
                print(f"ERROR: General processing error for file {idx + 1}: {processing_error}")
                errors_encountered.append(f"Processing error: {str(processing_error)}")
                continue

        # Step 6: Send final status with navigation buttons
        try:
            if sent_count > 0:
                final_text = f"✅ Successfully sent {sent_count} random files!"
                if errors_encountered:
                    final_text += f"\n\n⚠️ {len(errors_encountered)} files had issues (check logs)"
            else:
                final_text = "❌ No valid files could be sent."
                if errors_encountered:
                    final_text += f"\n\nErrors encountered:\n• " + "\n• ".join(errors_encountered[:3])
                    if len(errors_encountered) > 3:
                        final_text += f"\n• ... and {len(errors_encountered) - 3} more"

            nav_buttons = [
                InlineKeyboardButton("🎲 More Random", callback_data="rand_new"),
                InlineKeyboardButton("🔥 Popular", callback_data="rand_popular")
            ]
            more_buttons = [
                InlineKeyboardButton("🆕 Recent", callback_data="rand_recent"),
                InlineKeyboardButton("📊 Stats", callback_data="rand_stats")
            ]

            buttons = [nav_buttons, more_buttons]

            await loading_msg.edit_text(
                final_text,
                reply_markup=InlineKeyboardMarkup(buttons)
            )

            print(f"DEBUG: Final status - Sent: {sent_count}, Errors: {len(errors_encountered)}")

        except Exception as final_error:
            print(f"ERROR: Failed to send final status message: {final_error}")
            try:
                await loading_msg.edit_text(f"⚠️ Process completed but status update failed: {str(final_error)}")
            except:
                pass

    except Exception as main_error:
        error_text = f"❌ Critical error in random files process: {str(main_error)}"
        print(f"CRITICAL ERROR: Main process failed: {main_error}")

        try:
            if loading_msg:
                await loading_msg.edit_text(error_text)
            else:
                await message.reply_text(error_text)
        except Exception as msg_error:
            print(f"ERROR: Could not send error message: {msg_error}")

async def show_popular_files(client: Client, callback_query: CallbackQuery):
    """Show popular files"""
    try:
        # Determine clone ID to use the correct database
        clone_id = getattr(client, 'clone_id', None)
        if clone_id is None:
            bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
            if bot_token != Config.BOT_TOKEN:
                from bot.database.clone_db import get_clone_by_bot_token
                clone_data = await get_clone_by_bot_token(bot_token)
                if clone_data:
                    clone_id = clone_data.get('id')

        if clone_id is None:
            await callback_query.message.edit_text("❌ Error: Cannot determine clone ID. Please ensure this is a valid clone bot.")
            return

        # Updated to use clone_id for database selection
        files = await get_popular_files(limit=10, clone_id=clone_id)

        if not files:
            await callback_query.message.edit_text("📊 No popular files found.")
            return

        text = "🔥 **Popular Files**\n\n"
        buttons = []

        for file_data in files:
            file_name = file_data.get('file_name', 'Unknown')
            file_type = file_data.get('file_type', 'unknown')
            access_count = file_data.get('access_count', 0)

            display_name = file_name[:35] + "..." if len(file_name) > 35 else file_name
            button_text = f"{file_type.upper()} • {display_name} ({access_count} views)"

            file_link = encode(file_data['_id'])
            buttons.append([InlineKeyboardButton(
                button_text,
                url=f"https://t.me/{client.username}?start={file_link}"
            )])

        buttons.append([
            InlineKeyboardButton("🎲 Random", callback_data="rand_new"),
            InlineKeyboardButton("🆕 Recent", callback_data="rand_recent")
        ])
        buttons.append([InlineKeyboardButton("📊 Stats", callback_data="rand_stats")])

        await callback_query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        print(f"Error in show_popular_files: {e}")
        await callback_query.message.edit_text(f"❌ Error: {str(e)}")

async def show_recent_files(client: Client, callback_query: CallbackQuery):
    """Show recent files"""
    try:
        # Determine clone ID to use the correct database
        clone_id = getattr(client, 'clone_id', None)
        if clone_id is None:
            bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
            if bot_token != Config.BOT_TOKEN:
                from bot.database.clone_db import get_clone_by_bot_token
                clone_data = await get_clone_by_bot_token(bot_token)
                if clone_data:
                    clone_id = clone_data.get('id')

        if clone_id is None:
            await callback_query.message.edit_text("❌ Error: Cannot determine clone ID. Please ensure this is a valid clone bot.")
            return

        # Updated to use clone_id for database selection
        files = await get_recent_files(limit=10, clone_id=clone_id)

        if not files:
            await callback_query.message.edit_text("📊 No recent files found.")
            return

        text = "🆕 **Recent Files**\n\n"
        buttons = []

        for file_data in files:
            file_name = file_data.get('file_name', 'Unknown')
            file_type = file_data.get('file_type', 'unknown')

            display_name = file_name[:40] + "..." if len(file_name) > 40 else file_name
            button_text = f"{file_type.upper()} • {display_name}"

            file_link = encode(file_data['_id'])
            buttons.append([InlineKeyboardButton(
                button_text,
                url=f"https://t.me/{client.username}?start={file_link}"
            )])

        buttons.append([
            InlineKeyboardButton("🎲 Random", callback_data="rand_new"),
            InlineKeyboardButton("🔥 Popular", callback_data="rand_popular")
        ])
        buttons.append([InlineKeyboardButton("📊 Stats", callback_data="rand_stats")])

        await callback_query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        print(f"Error in show_recent_files: {e}")
        await callback_query.message.edit_text(f"❌ Error: {str(e)}")

async def show_index_stats(client: Client, callback_query: CallbackQuery):
    """Show indexing statistics"""
    try:
        # Determine clone ID to use the correct database
        clone_id = getattr(client, 'clone_id', None)
        if clone_id is None:
            bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
            if bot_token != Config.BOT_TOKEN:
                from bot.database.clone_db import get_clone_by_bot_token
                clone_data = await get_clone_by_bot_token(bot_token)
                if clone_data:
                    clone_id = clone_data.get('id')

        if clone_id is None:
            await callback_query.message.edit_text("❌ Error: Cannot determine clone ID. Please ensure this is a valid clone bot.")
            return

        # Updated to use clone_id for database selection
        stats = await get_index_stats(clone_id=clone_id)

        text = "📊 **Database Statistics**\n\n"
        text += f"**Total Files:** {stats['total_files']}\n\n"

        if stats['file_types']:
            text += "**File Types:**\n"
            for file_type, count in stats['file_types'].items():
                text += f"• {file_type.title()}: {count}\n"

        buttons = [
            [
                InlineKeyboardButton("🎲 Random", callback_data="rand_new"),
                InlineKeyboardButton("🔥 Popular", callback_data="rand_popular")
            ],
            [InlineKeyboardButton("🆕 Recent", callback_data="rand_recent")]
        ]

        await callback_query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        print(f"Error in show_index_stats: {e}")
        await callback_query.message.edit_text(f"❌ Error: {str(e)}")

# Store user offset for recent files to ensure different files each time
user_recent_offsets = {}

async def handle_recent_files_direct(client: Client, message, is_callback: bool = False):
    """Enhanced recent files handler with better sorting and presentation"""
    loading_msg = None

    try:
        # Check force subscription first
        if await handle_force_sub(client, message):
            return

        # Check if the recent feature is enabled
        if not await check_feature_enabled(client, 'recent'):
            await message.reply_text("❌ Recent files feature is currently disabled by the admin.")
            return

        user_id = message.from_user.id if hasattr(message, 'from_user') else None
        if not user_id:
            await message.reply_text("❌ Could not identify user.")
            return

        # Check command limit
        if not await use_command(user_id, client):
            needs_verification, remaining = await check_command_limit(user_id, client)
            token_settings = await TokenVerificationManager.get_clone_token_settings(client)
            verification_mode = token_settings.get('verification_mode', 'command_limit')

            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ])

            if verification_mode == 'time_based':
                duration = token_settings.get('time_duration', 24)
                message_text = f"⚠️ **Verification Required!**\n\n🕐 Get {duration} hours of unlimited access!"
            else:
                command_limit = token_settings.get('command_limit', 3)
                message_text = f"⚠️ **Command Limit Reached!**\n\nGet {command_limit} more commands with verification!"

            await message.reply_text(message_text, reply_markup=buttons)
            return

        # Determine clone ID
        clone_id = getattr(client, 'clone_id', None)
        if clone_id is None:
            bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
            if bot_token != Config.BOT_TOKEN:
                from bot.database.clone_db import get_clone_by_bot_token
                clone_data = await get_clone_by_bot_token(bot_token)
                if clone_data:
                    clone_id = clone_data.get('id')

        # Initialize loading message
        if is_callback:
            loading_msg = await message.edit_text("🆕 Fetching recently added files...")
        else:
            loading_msg = await message.reply_text("🆕 Fetching recently added files...")

        # Enhanced recent files query with date-based sorting
        try:
            from bot.database.mongo_db import collection
            from datetime import datetime, timedelta

            # Get files added in last 7 days, sorted by most recent
            recent_date = datetime.utcnow() - timedelta(days=7)

            pipeline = [
                {
                    "$match": {
                        "file_type": {"$in": ["video", "document", "photo", "audio", "animation"]},
                        "file_name": {"$exists": True, "$ne": "", "$ne": None},
                        "file_size": {"$gt": 1024},
                        "indexed_at": {"$gte": recent_date}
                    }
                },
                {
                    "$addFields": {
                        "freshness_score": {
                            "$add": [
                                {"$divide": [
                                    {"$subtract": ["$indexed_at", recent_date]},
                                    86400000  # Convert to days
                                ]},
                                {"$multiply": [{"$ifNull": ["$file_size", 0]}, 0.000001]}  # Size bonus
                            ]
                        }
                    }
                },
                {"$sort": {"freshness_score": -1, "indexed_at": -1}},
                {"$limit": 8}
            ]

            if clone_id:
                pipeline[0]["$match"]["clone_id"] = clone_id

            cursor = collection.aggregate(pipeline)
            results = await cursor.to_list(length=8)

            # Fallback to general recent files if no recent files found
            if not results:
                fallback_query = {
                    "file_type": {"$in": ["video", "document", "photo", "audio"]},
                    "file_name": {"$exists": True, "$ne": ""}
                }
                if clone_id:
                    fallback_query["clone_id"] = clone_id

                cursor = collection.find(fallback_query).sort("_id", -1).limit(5)
                results = await cursor.to_list(length=5)

        except Exception as db_error:
            print(f"ERROR: Recent files database query failed: {db_error}")
            await loading_msg.edit_text("❌ Database error. Please try again.")
            return

        if not results:
            await loading_msg.edit_text("❌ No recent files found. Files will appear here when added.")
            return

        await loading_msg.edit_text(f"📁 Sending {len(results)} recently added files...")

        # Send recent files with enhanced presentation
        sent_count = 0
        for idx, file_data in enumerate(results):
            try:
                file_id = str(file_data.get('_id', ''))
                file_name = file_data.get('file_name', 'Unknown File')
                file_size = file_data.get('file_size', 0)
                indexed_at = file_data.get('indexed_at')

                # Calculate time since added
                if indexed_at:
                    time_diff = datetime.utcnow() - indexed_at
                    if time_diff.days > 0:
                        time_str = f"{time_diff.days} days ago"
                    elif time_diff.seconds > 3600:
                        hours = time_diff.seconds // 3600
                        time_str = f"{hours} hours ago"
                    else:
                        minutes = time_diff.seconds // 60
                        time_str = f"{minutes} minutes ago"
                else:
                    time_str = "Recently"

                # Extract message ID
                if '_' in file_id:
                    message_id = int(file_id.split('_')[-1])
                else:
                    message_id = int(file_id)

                # Get message from database channel
                db_message = await client.get_messages(Config.INDEX_CHANNEL_ID, message_id)

                if db_message and db_message.media:
                    # Create enhanced caption with freshness info
                    size_str = get_readable_file_size(file_size) if file_size else "Unknown"
                    caption = f"🆕 **{file_name}**\n📊 Size: {size_str}\n⏰ Added: {time_str}"

                    # Enhanced keyboard for recent files
                    keyboard = InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("🆕 More Recent", callback_data="recent_more"),
                            InlineKeyboardButton("📤 Share", callback_data=f"share_{file_id}")
                        ],
                        [
                            InlineKeyboardButton("🎲 Random Files", callback_data="random_files"),
                            InlineKeyboardButton("🔥 Popular Files", callback_data="popular_files")
                        ]
                    ])

                    # Send based on media type
                    if db_message.photo:
                        await client.send_photo(
                            chat_id=message.chat.id,
                            photo=db_message.photo.file_id,
                            caption=caption,
                            reply_markup=keyboard
                        )
                    elif db_message.video:
                        await client.send_video(
                            chat_id=message.chat.id,
                            video=db_message.video.file_id,
                            caption=caption,
                            reply_markup=keyboard
                        )
                    elif db_message.document:
                        await client.send_document(
                            chat_id=message.chat.id,
                            document=db_message.document.file_id,
                            caption=caption,
                            reply_markup=keyboard
                        )
                    elif db_message.audio:
                        await client.send_audio(
                            chat_id=message.chat.id,
                            audio=db_message.audio.file_id,
                            caption=caption,
                            reply_markup=keyboard
                        )
                    elif db_message.animation:
                        await client.send_animation(
                            chat_id=message.chat.id,
                            animation=db_message.animation.file_id,
                            caption=caption,
                            reply_markup=keyboard
                        )

                    sent_count += 1

                    # Update access count
                    await collection.update_one(
                        {"_id": file_id},
                        {"$inc": {"access_count": 1}}
                    )

                    await asyncio.sleep(0.5)

            except Exception as send_error:
                print(f"ERROR: Failed to send recent file {idx + 1}: {send_error}")
                continue

        # Final status with navigation
        if sent_count > 0:
            final_buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🆕 More Recent", callback_data="recent_more"),
                    InlineKeyboardButton("🎲 Random", callback_data="random_files")
                ],
                [
                    InlineKeyboardButton("🔥 Popular", callback_data="popular_files"),
                    InlineKeyboardButton("📊 Statistics", callback_data="file_stats")
                ]
            ])

            await loading_msg.edit_text(
                f"✅ Sent {sent_count} recently added files!\n\n"
                f"🆕 These are the latest files added to the database.\n"
                f"📈 Use buttons below to explore more content.",
                reply_markup=final_buttons
            )
        else:
            await loading_msg.edit_text("❌ No recent files could be sent. Try again later.")

    except Exception as main_error:
        print(f"CRITICAL ERROR in recent files: {main_error}")
        try:
            if loading_msg:
                await loading_msg.edit_text("❌ An unexpected error occurred. Please try again.")
        except:
            pass

async def handle_popular_files_direct(client: Client, message, is_callback: bool = False):
    """Enhanced popular files handler with advanced popularity scoring"""
    loading_msg = None

    try:
        # Check force subscription first
        if await handle_force_sub(client, message):
            return

        # Check if the popular feature is enabled
        if not await check_feature_enabled(client, 'popular'):
            await message.reply_text("❌ Most popular files feature is currently disabled by the admin.")
            return

        user_id = message.from_user.id if hasattr(message, 'from_user') else None
        if not user_id:
            await message.reply_text("❌ Could not identify user.")
            return

        # Check command limit
        if not await use_command(user_id, client):
            needs_verification, remaining = await check_command_limit(user_id, client)
            token_settings = await TokenVerificationManager.get_clone_token_settings(client)
            verification_mode = token_settings.get('verification_mode', 'command_limit')

            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ])

            if verification_mode == 'time_based':
                duration = token_settings.get('time_duration', 24)
                message_text = f"⚠️ **Verification Required!**\n\n🕐 Get {duration} hours of unlimited access!"
            else:
                command_limit = token_settings.get('command_limit', 3)
                message_text = f"⚠️ **Command Limit Reached!**\n\nGet {command_limit} more commands with verification!"

            await message.reply_text(message_text, reply_markup=buttons)
            return

        # Determine clone ID
        clone_id = getattr(client, 'clone_id', None)
        if clone_id is None:
            bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
            if bot_token != Config.BOT_TOKEN:
                from bot.database.clone_db import get_clone_by_bot_token
                clone_data = await get_clone_by_bot_token(bot_token)
                if clone_data:
                    clone_id = clone_data.get('id')

        # Initialize loading message
        if is_callback:
            loading_msg = await message.edit_text("🔥 Finding most popular files...")
        else:
            loading_msg = await message.reply_text("🔥 Finding most popular files...")

        # Enhanced popular files query with advanced scoring
        try:
            from bot.database.mongo_db import collection
            from datetime import datetime, timedelta

            # Advanced popularity algorithm considering multiple factors
            pipeline = [
                {
                    "$match": {
                        "file_type": {"$in": ["video", "document", "photo", "audio", "animation"]},
                        "file_name": {"$exists": True, "$ne": "", "$ne": None},
                        "file_size": {"$gt": 1024},
                        "access_count": {"$gte": 1}  # Must have at least 1 view
                    }
                },
                {
                    "$addFields": {
                        "popularity_score": {
                            "$add": [
                                # Base popularity from access count (70% weight)
                                {"$multiply": [{"$ifNull": ["$access_count", 0]}, 0.7]},

                                # Download count bonus (20% weight)
                                {"$multiply": [{"$ifNull": ["$download_count", 0]}, 0.2]},

                                # File size bonus for larger files (5% weight)
                                {"$multiply": [
                                    {"$cond": [
                                        {"$gte": ["$file_size", 52428800]},  # 50MB+
                                        5,
                                        {"$cond": [
                                            {"$gte": ["$file_size", 10485760]},  # 10MB+
                                            2,
                                            1
                                        ]}
                                    ]}, 0.05
                                ]},

                                # Recency bonus (5% weight) - newer files get slight boost
                                {"$multiply": [
                                    {"$cond": [
                                        {"$gte": ["$indexed_at", {"$subtract": [datetime.utcnow(), 604800000]}]},  # Last week
                                        3,
                                        {"$cond": [
                                            {"$gte": ["$indexed_at", {"$subtract": [datetime.utcnow(), 2592000000]}]},  # Last month
                                            1,
                                            0
                                        ]}
                                    ]}, 0.05
                                ]}
                            ]
                        },

                        # Calculate engagement rate
                        "engagement_rate": {
                            "$divide": [
                                {"$add": [
                                    {"$ifNull": ["$access_count", 0]},
                                    {"$multiply": [{"$ifNull": ["$download_count", 0]}, 2]}
                                ]},
                                {"$add": [
                                    {"$divide": [
                                        {"$subtract": [datetime.utcnow(), {"$ifNull": ["$indexed_at", datetime.utcnow()]}]},
                                        86400000  # Days since indexed
                                    ]},
                                    1
                                ]}
                            ]
                        }
                    }
                },
                {
                    "$sort": {
                        "popularity_score": -1,
                        "engagement_rate": -1,
                        "access_count": -1
                    }
                },
                {"$limit": 8}
            ]

            if clone_id:
                pipeline[0]["$match"]["clone_id"] = clone_id

            cursor = collection.aggregate(pipeline)
            results = await cursor.to_list(length=8)

            # Fallback to simple access count sorting if no results
            if not results:
                fallback_query = {
                    "file_type": {"$in": ["video", "document", "photo", "audio"]},
                    "file_name": {"$exists": True, "$ne": ""},
                    "access_count": {"$gte": 1}
                }
                if clone_id:
                    fallback_query["clone_id"] = clone_id

                cursor = collection.find(fallback_query).sort("access_count", -1).limit(5)
                results = await cursor.to_list(length=5)

        except Exception as db_error:
            print(f"ERROR: Popular files database query failed: {db_error}")
            await loading_msg.edit_text("❌ Database error. Please try again.")
            return

        if not results:
            await loading_msg.edit_text("❌ No popular files found yet. Files become popular as users access them.")
            return

        await loading_msg.edit_text(f"📁 Sending {len(results)} most popular files...")

        # Send popular files with enhanced presentation
        sent_count = 0
        for idx, file_data in enumerate(results):
            try:
                file_id = str(file_data.get('_id', ''))
                file_name = file_data.get('file_name', 'Unknown File')
                file_size = file_data.get('file_size', 0)
                access_count = file_data.get('access_count', 0)
                download_count = file_data.get('download_count', 0)
                popularity_score = file_data.get('popularity_score', 0)

                # Calculate popularity rank
                rank_emoji = ["🥇", "🥈", "🥉", "🏅", "⭐"][min(idx, 4)]

                # Extract message ID
                if '_' in file_id:
                    message_id = int(file_id.split('_')[-1])
                else:
                    message_id = int(file_id)

                # Get message from database channel
                db_message = await client.get_messages(Config.INDEX_CHANNEL_ID, message_id)

                if db_message and db_message.media:
                    # Create enhanced caption with popularity metrics
                    size_str = get_readable_file_size(file_size) if file_size else "Unknown"
                    total_interactions = access_count + (download_count * 2)

                    caption = (f"{rank_emoji} **Popular #{idx + 1}:** {file_name}\n"
                              f"📊 Size: {size_str}\n"
                              f"👁️ Views: {access_count:,}\n"
                              f"⬇️ Downloads: {download_count:,}\n"
                              f"🔥 Popularity Score: {popularity_score:.1f}")

                    # Enhanced keyboard for popular files
                    keyboard = InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("🔥 More Popular", callback_data="popular_more"),
                            InlineKeyboardButton("📤 Share", callback_data=f"share_{file_id}")
                        ],
                        [
                            InlineKeyboardButton("📈 File Stats", callback_data=f"stats_{file_id}"),
                            InlineKeyboardButton("🎲 Random", callback_data="random_files")
                        ]
                    ])

                    # Send based on media type
                    if db_message.photo:
                        await client.send_photo(
                            chat_id=message.chat.id,
                            photo=db_message.photo.file_id,
                            caption=caption,
                            reply_markup=keyboard
                        )
                    elif db_message.video:
                        await client.send_video(
                            chat_id=message.chat.id,
                            video=db_message.video.file_id,
                            caption=caption,
                            reply_markup=keyboard
                        )
                    elif db_message.document:
                        await client.send_document(
                            chat_id=message.chat.id,
                            document=db_message.document.file_id,
                            caption=caption,
                            reply_markup=keyboard
                        )
                    elif db_message.audio:
                        await client.send_audio(
                            chat_id=message.chat.id,
                            audio=db_message.audio.file_id,
                            caption=caption,
                            reply_markup=keyboard
                        )
                    elif db_message.animation:
                        await client.send_animation(
                            chat_id=message.chat.id,
                            animation=db_message.animation.file_id,
                            caption=caption,
                            reply_markup=keyboard
                        )

                    sent_count += 1

                    # Update access count and popularity metrics
                    await collection.update_one(
                        {"_id": file_id},
                        {
                            "$inc": {"access_count": 1},
                            "$set": {"last_accessed": datetime.utcnow()}
                        }
                    )

                    await asyncio.sleep(0.5)

            except Exception as send_error:
                print(f"ERROR: Failed to send popular file {idx + 1}: {send_error}")
                continue

        # Final status with popularity insights
        if sent_count > 0:
            total_views = sum(f.get('access_count', 0) for f in results[:sent_count])
            avg_views = total_views // sent_count if sent_count > 0 else 0

            final_buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔥 More Popular", callback_data="popular_more"),
                    InlineKeyboardButton("🎲 Random", callback_data="random_files")
                ],
                [
                    InlineKeyboardButton("🆕 Recent", callback_data="recent_files"),
                    InlineKeyboardButton("📊 Full Statistics", callback_data="detailed_stats")
                ]
            ])

            await loading_msg.edit_text(
                f"🔥 Sent {sent_count} most popular files!\n\n"
                f"📈 Total views: {total_views:,}\n"
                f"📊 Average views: {avg_views:,}\n\n"
                f"🎯 These files are trending among users!",
                reply_markup=final_buttons
            )
        else:
            await loading_msg.edit_text("❌ No popular files could be sent. Try again later.")

    except Exception as main_error:
        print(f"CRITICAL ERROR in popular files: {main_error}")
        try:
            if loading_msg:
                await loading_msg.edit_text("❌ An unexpected error occurred. Please try again.")
        except:
            pass

# Store user offset for popular files to ensure different files each time
user_popular_offsets = {}

# Aliases for backward compatibility with callback.py imports
async def handle_recent_files(client: Client, message: Message, is_callback: bool = False, skip_command_check: bool = False):
    """Alias for handle_recent_files_direct"""
    # Check if the recent feature is enabled before proceeding
    if not await check_feature_enabled(client, 'recent'):
        await message.reply_text("❌ Recent files feature is currently disabled by the admin.")
        return
    return await handle_recent_files_direct(client, message, is_callback)

async def handle_popular_files(client: Client, message: Message, is_callback: bool = False, skip_command_check: bool = False):
    """Alias for handle_popular_files_direct"""
    # Check if the popular feature is enabled before proceeding
    if not await check_feature_enabled(client, 'popular'):
        await message.reply_text("❌ Most popular files feature is currently disabled by the admin.")
        return
    return await handle_popular_files_direct(client, message, is_callback)

@Client.on_message(filters.command("popular") & filters.private)
async def popular_files_command(client: Client, message: Message):
    """Command to get popular files directly"""
    try:
        # Check force subscription first
        if await handle_force_sub(client, message):
            return

        # Check if the popular feature is enabled
        if not await check_feature_enabled(client, 'popular'):
            await message.reply_text("❌ Most popular files feature is currently disabled by the admin.")
            return

        user_id = message.from_user.id

        # Check command limit and use command if allowed
        if not await use_command(user_id, client):
            needs_verification, remaining = await check_command_limit(user_id, client)

            # Get verification mode for appropriate message
            token_settings = await TokenVerificationManager.get_clone_token_settings(client)
            verification_mode = token_settings.get('verification_mode', 'command_limit')

            # Create verification button
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ])

            if verification_mode == 'time_based':
                duration = token_settings.get('time_duration', 24)
                message_text = (
                    f"⚠️ **Verification Required!**\n\n"
                    f"🕐 **Time-Based Access:** Get {duration} hours of unlimited commands!\n\n"
                    f"🔓 **Get instant access by:**\n"
                    f"• Getting a verification token ({duration}h unlimited access)\n"
                    f"• Upgrading to Premium (permanent unlimited access)\n\n"
                    f"💡 Premium users get unlimited access without verification!"
                )
            else:
                command_limit = token_settings.get('command_limit', 3)
                message_text = (
                    f"⚠️ **Command Limit Reached!**\n\n"
                    f"You've used all your free commands.\n\n"
                    f"🔓 **Get instant access by:**\n"
                    f"• Getting a verification token ({command_limit} more commands)\n"
                    f"• Upgrading to Premium (unlimited commands)\n\n"
                    f"💡 Premium users get unlimited access without verification!"
                )

            await message.reply_text(message_text, reply_markup=buttons)
            return

        await handle_popular_files_direct(client, message, is_callback=False)
    except Exception as e:
        print(f"Error in popular_files_command: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")


@Client.on_message(filters.command("recent") & filters.private)
async def recent_files_command(client: Client, message: Message):
    """Command to get recent files directly"""
    try:
        # Check force subscription first
        if await handle_force_sub(client, message):
            return

        # Check if the recent feature is enabled
        if not await check_feature_enabled(client, 'recent'):
            await message.reply_text("❌ Recent files feature is currently disabled by the admin.")
            return

        user_id = message.from_user.id

        # Check command limit and use command if allowed
        if not await use_command(user_id, client):
            needs_verification, remaining = await check_command_limit(user_id, client)

            # Get verification mode for appropriate message
            token_settings = await TokenVerificationManager.get_clone_token_settings(client)
            verification_mode = token_settings.get('verification_mode', 'command_limit')

            # Create verification button
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ])

            if verification_mode == 'time_based':
                duration = token_settings.get('time_duration', 24)
                message_text = (
                    f"⚠️ **Verification Required!**\n\n"
                    f"🕐 **Time-Based Access:** Get {duration} hours of unlimited commands!\n\n"
                    f"🔓 **Get instant access by:**\n"
                    f"• Getting a verification token ({duration}h unlimited access)\n"
                    f"• Upgrading to Premium (permanent unlimited access)\n\n"
                    f"💡 Premium users get unlimited access without verification!"
                )
            else:
                command_limit = token_settings.get('command_limit', 3)
                message_text = (
                    f"⚠️ **Command Limit Reached!**\n\n"
                    f"You've used all your free commands.\n\n"
                    f"🔓 **Get instant access by:**\n"
                    f"• Getting a verification token ({command_limit} more commands)\n"
                    f"• Upgrading to Premium (unlimited commands)\n\n"
                    f"💡 Premium users get unlimited access without verification!"
                )

            await message.reply_text(message_text, reply_markup=buttons)
            return

        await handle_recent_files_direct(client, message, is_callback=False)
    except Exception as e:
        print(f"Error in recent_files_command: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")
# Mother bot redirection for file commands
@Client.on_message(filters.command(["rand", "random", "recent", "popular", "search"]) & filters.private)
async def redirect_file_commands(client: Client, message: Message):
    """Redirect users to create clone for file features if on mother bot"""
    user_id = message.from_user.id
    command = message.command[0]

    # Detect if this is mother bot
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    is_clone_bot = (
        bot_token != Config.BOT_TOKEN or
        hasattr(client, 'is_clone') and client.is_clone or
        hasattr(client, 'clone_config') and client.clone_config or
        hasattr(client, 'clone_data')
    )

    # Only show redirect message in mother bot
    if not is_clone_bot and bot_token == Config.BOT_TOKEN:
        text = f"🤖 **File Features Not Available Here**\n\n"
        text += f"The `/{command}` command is only available in **clone bots**, not in the mother bot.\n\n"
        text += f"🔧 **How to access file features:**\n"
        text += f"1. Create your personal clone bot with `/createclone`\n"
        text += f"2. Use your clone bot to access:\n"
        text += f"   • 🎲 Random files\n"
        text += f"   • 🆕 Recent files\n"
        text += f"   • 🔥 Most popular files\n\n"
        text += f"💡 **Why use clones?**\n"
        text += f"Clone bots provide dedicated file sharing while keeping the mother bot clean for management tasks."

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Create Clone Bot", callback_data="start_clone_creation")],
            [InlineKeyboardButton("📋 Manage My Clones", callback_data="manage_my_clone")]
        ])

        await message.reply_text(text, reply_markup=buttons)

@Client.on_message(filters.private & filters.text & filters.regex(r"^(🎲 Random|🆕 Recent Added|🔥 Most Popular|🎲 Random Files)$"))
async def redirect_keyboard_handlers(client: Client, message: Message):
    """Handle keyboard buttons for file features - redirect on mother bot"""
    button_text = message.text

    # Detect if this is mother bot
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    is_clone_bot = (
        bot_token != Config.BOT_TOKEN or
        hasattr(client, 'is_clone') and client.is_clone or
        hasattr(client, 'clone_config') and client.clone_config or
        hasattr(client, 'clone_data')
    )

    # Only show redirect message in mother bot
    if not is_clone_bot and bot_token == Config.BOT_TOKEN:
        text = f"🤖 **Feature Not Available in Mother Bot**\n\n"
        text += f"The **{button_text}** feature is only available in clone bots.\n\n"
        text += f"🔧 **Get Access:**\n"
        text += f"1. Create your clone bot: `/createclone`\n"
        text += f"2. Use your clone for file features\n\n"
        text += f"💡 This keeps the mother bot focused on clone management!"

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Create Clone Bot", callback_data="start_clone_creation")]
        ])
        await message.reply_text(text, reply_markup=buttons)
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.logging import LOGGER

logger = LOGGER(__name__)

@Client.on_message(filters.command("search") & filters.private)
async def search_command(client: Client, message: Message):
    """Handle search command"""
    try:
        if len(message.command) < 2:
            await message.reply_text("❌ **Usage:** `/search <query>`\n\nExample: `/search funny videos`")
            return

        query = " ".join(message.command[1:])

        text = f"🔍 **Search Results for:** `{query}`\n\n"
        text += f"⚠️ Search functionality is currently under development.\n"
        text += f"Please try again later!"

        await message.reply_text(text)
        logger.info(f"Search query '{query}' from user {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error in search command: {e}")
        await message.reply_text("❌ Search error occurred. Please try again.")

async def handle_random_files(client, message, is_callback=False, skip_command_check=False):
    """Handle random files request"""
    try:
        text = "🎲 **Random Files**\n\n"
        text += "⚠️ Random file feature is currently under development.\n"
        text += "Please check back later!"

        if is_callback:
            await message.edit_text(text)
        else:
            await message.reply_text(text)

    except Exception as e:
        logger.error(f"Error in handle_random_files: {e}")