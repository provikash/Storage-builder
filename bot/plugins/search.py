from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from bot.database import get_random_files, get_popular_files, get_recent_files, get_index_stats, increment_access_count, is_premium_user
from bot.utils import encode, get_readable_file_size, handle_force_sub
from bot.utils.command_verification import check_command_limit, use_command
# Rate limiter removed
from info import Config
import asyncio
import traceback

# --- Feature Checking Function ---
async def check_feature_enabled(client: Client, feature_name: str) -> bool:
    """Check if a feature is enabled for the current bot"""
    try:
        bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)

        # Mother bot has all features enabled
        if bot_token == Config.BOT_TOKEN:
            return True

        # For clone bots, check the database
        from bot.database.clone_db import get_clone_by_bot_token
        clone_data = await get_clone_by_bot_token(bot_token)

        if not clone_data:
            # If clone data not found, assume feature is disabled or handle as an error
            print(f"WARNING: Clone data not found for bot token {bot_token}. Assuming feature '{feature_name}' is disabled.")
            return False

        # Return the enabled status of the feature, default to True if not specified
        return clone_data.get(f'{feature_name}_mode', True)
    except Exception as e:
        print(f"Error checking feature {feature_name}: {e}")
        return False

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
        if not await use_command(user_id):
            needs_verification, remaining = await check_command_limit(user_id)

            # Create verification button
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ])

            await message.reply_text(
                f"⚠️ **Command Limit Reached!**\n\n"
                f"You've used all your free commands (3/3).\n\n"
                f"🔓 **Get instant access by:**\n"
                f"• Getting a verification token (with ads)\n"
                f"• Upgrading to Premium (no ads)\n\n"
                f"💡 Premium users get unlimited access without verification!",
                reply_markup=buttons
            )
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
        needs_verification, remaining = await check_command_limit(user_id)

        # Only show verification dialog if user actually needs verification AND has no remaining commands
        if needs_verification and remaining <= 0:
            # Create verification button
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ])

            await message.reply_text(
                f"⚠️ **Command Limit Reached!**\n\n"
                f"You've used all your free commands (3/3).\n\n"
                f"🔓 **Get instant access by:**\n"
                f"• Getting a verification token (with ads)\n"
                f"• Upgrading to Premium (no ads)\n\n"
                f"💡 Premium users get unlimited access without verification!",
                reply_markup=buttons
            )
            return

        # Try to use command (this will handle admin/premium logic internally)
        if not await use_command(user_id):
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
        needs_verification, remaining = await check_command_limit(user_id)

        # Only show verification dialog if user actually needs verification AND has no remaining commands
        if needs_verification and remaining <= 0:
            # Create verification button
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ])

            await message.reply_text(
                f"⚠️ **Command Limit Reached!**\n\n"
                f"You've used all your free commands (3/3).\n\n"
                f"🔓 **Get instant access by:**\n"
                f"• Getting a verification token (with ads)\n"
                f"• Upgrading to Premium (no ads)\n\n"
                f"💡 Premium users get unlimited access without verification!",
                reply_markup=buttons
            )
            return

        # Try to use command (this will handle admin/premium logic internally)
        if not await use_command(user_id):
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
        needs_verification, remaining = await check_command_limit(user_id)

        # Only show verification dialog if user actually needs verification AND has no remaining commands
        if needs_verification and remaining <= 0:
            # Create verification button
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ])

            await message.reply_text(
                f"⚠️ **Command Limit Reached!**\n\n"
                f"You've used all your free commands (3/3).\n\n"
                f"🔓 **Get instant access by:**\n"
                f"• Getting a verification token (with ads)\n"
                f"• Upgrading to Premium (no ads)\n\n"
                f"💡 Premium users get unlimited access without verification!",
                reply_markup=buttons
            )
            return

        # Try to use command (this will handle admin/premium logic internally)
        if not await use_command(user_id):
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
        needs_verification, remaining = await check_command_limit(user_id)

        if needs_verification:
            buttons = [
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ]
            await message.reply_text(
                "🔐 **Verification Required!**\n\nYou need to verify your account to continue. Get a verification token to access 3 more commands!",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            return

        # Try to use command
        if not await use_command(user_id):
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
        # Initialize loading message
        if is_callback:
            loading_msg = await message.edit_text("🎲 Getting random files...")
        else:
            loading_msg = await message.reply_text("🎲 Getting random files...")

        print("DEBUG: Starting random files retrieval process...")

        # Step 1: Query MongoDB for file metadata
        try:
            results = await get_random_files(limit=15)  # Get more to account for invalid files
            print(f"DEBUG: Retrieved {len(results)} files from database")
        except Exception as db_error:
            error_msg = f"❌ Database query failed: {str(db_error)}"
            print(f"ERROR: MongoDB query failed: {db_error}")
            await loading_msg.edit_text(error_msg)
            return

        if not results:
            text = "❌ No files found in database."
            print("DEBUG: No files found in database")
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
        files = await get_popular_files(limit=10)

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
        files = await get_recent_files(limit=10)

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
        stats = await get_index_stats()

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
    """Get and send 5 recent files directly to user, with different files each time"""
    loading_msg = None

    try:
        user_id = message.from_user.id if hasattr(message, 'from_user') and message.from_user else message.chat.id

        # Initialize loading message
        if is_callback:
            loading_msg = await message.edit_text("🆕 Getting recent files...")
        else:
            loading_msg = await message.reply_text("🆕 Getting recent files...")

        print(f"DEBUG: Starting recent files retrieval for user {user_id}")

        # Get current offset for this user (defaults to 0)
        current_offset = user_recent_offsets.get(user_id, 0)
        print(f"DEBUG: Current offset for user {user_id}: {current_offset}")

        # Step 1: Query MongoDB for recent file metadata with offset
        try:
            results = await get_recent_files(limit=10, offset=current_offset)  # Get more to account for invalid files
            print(f"DEBUG: Retrieved {len(results)} recent files from database with offset {current_offset}")
        except Exception as db_error:
            error_msg = f"❌ Database query failed: {str(db_error)}"
            print(f"ERROR: MongoDB query failed: {db_error}")
            await loading_msg.edit_text(error_msg)
            return

        if not results:
            # Reset offset if no more files and try again
            if current_offset > 0:
                user_recent_offsets[user_id] = 0
                results = await get_recent_files(limit=10, offset=0)
                print(f"DEBUG: Reset offset, retrieved {len(results)} files")

            if not results:
                await loading_msg.edit_text("❌ No recent files found in database.")
                return

        try:
            await loading_msg.edit_text(f"📁 Processing {len(results)} recent files...")
        except Exception as msg_error:
            print(f"WARNING: Failed to update loading message: {msg_error}")

        # Step 2: Send 5 recent files directly to user
        sent_count = 0
        target_count = 5  # Target number of files to send
        errors_encountered = []

        for idx, file_data in enumerate(results):
            if sent_count >= target_count:
                print(f"DEBUG: Reached target count of {target_count} files")
                break

            print(f"DEBUG: Processing recent file {idx + 1}/{len(results)}")

            try:
                # Extract metadata from MongoDB document with validation
                if not isinstance(file_data, dict):
                    print(f"ERROR: Invalid file_data type: {type(file_data)}")
                    errors_encountered.append(f"Invalid data structure for file {idx + 1}")
                    continue

                file_id = str(file_data.get('_id', ''))
                file_name = file_data.get('file_name', 'Unknown File')
                file_type = file_data.get('file_type', 'unknown')

                if not file_id:
                    print(f"ERROR: No file_id found for file: {file_name}")
                    errors_encountered.append(f"Missing file_id for {file_name}")
                    continue

                print(f"DEBUG: Processing recent file: {file_name} with ID: {file_id}, Type: {file_type}")

                # Parse file_id to extract message_id
                message_id = None
                try:
                    if '_' in file_id:
                        parts = file_id.split('_')
                        if len(parts) >= 2:
                            message_id = int(parts[-1])
                            print(f"DEBUG: Extracted message_id {message_id} from composite ID: {file_id}")
                        else:
                            print(f"ERROR: Invalid composite file_id format: {file_id}")
                            errors_encountered.append(f"Invalid ID format: {file_id}")
                            continue
                    else:
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

                # Retrieve file from Telegram
                try:
                    print(f"DEBUG: Fetching message {message_id} from channel {Config.INDEX_CHANNEL_ID}")
                    db_message = await client.get_messages(Config.INDEX_CHANNEL_ID, message_id)

                    if not db_message or db_message.empty or not db_message.media:
                        print(f"ERROR: Message {message_id} invalid or has no media")
                        errors_encountered.append(f"Message {message_id} invalid or no media")
                        continue

                    print(f"DEBUG: Successfully retrieved message {message_id} with media")

                except Exception as telegram_get_error:
                    print(f"ERROR: Telegram get_messages failed for message {message_id}: {telegram_get_error}")
                    errors_encountered.append(f"Get message {message_id}: {str(telegram_get_error)}")
                    continue

                # Send the file to user without caption but with custom keyboard
                try:
                    print(f"DEBUG: Sending recent media from message {message_id} to user {message.chat.id}")

                    # Create custom keyboard
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

                    # Send media based on type without caption
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
                        copied_msg = await db_message.copy(
                            chat_id=message.chat.id,
                            reply_markup=custom_keyboard,
                            protect_content=Config.PROTECT_CONTENT
                        )

                    if copied_msg:
                        sent_count += 1
                        print(f"SUCCESS: Sent recent file #{sent_count}: {file_name}")

                        # Increment access count
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

        # Update offset for next time (increment by files processed)
        user_recent_offsets[user_id] = current_offset + len(results)
        print(f"DEBUG: Updated offset for user {user_id} to {user_recent_offsets[user_id]}")

        # Send final status with navigation buttons
        try:
            if sent_count > 0:
                final_text = f"✅ Successfully sent {sent_count} recent files!"
                if errors_encountered:
                    final_text += f"\n\n⚠️ {len(errors_encountered)} files had issues (check logs)"
            else:
                final_text = "❌ No valid recent files could be sent."
                if errors_encountered:
                    final_text += f"\n\nErrors encountered:\n• " + "\n• ".join(errors_encountered[:3])
                    if len(errors_encountered) > 3:
                        final_text += f"\n• ... and {len(errors_encountered) - 3} more"

            nav_buttons = [
                InlineKeyboardButton("🆕 More Recent", callback_data="rand_recent"),
                InlineKeyboardButton("🎲 Random", callback_data="rand_new")
            ]
            more_buttons = [
                InlineKeyboardButton("🔥 Popular", callback_data="rand_popular"),
                InlineKeyboardButton("📊 Stats", callback_data="rand_stats")
            ]

            buttons = [nav_buttons, more_buttons]

            await loading_msg.edit_text(
                final_text,
                reply_markup=InlineKeyboardMarkup(buttons)
            )

            print(f"DEBUG: Recent files final status - Sent: {sent_count}, Errors: {len(errors_encountered)}")

        except Exception as final_error:
            print(f"ERROR: Failed to send final status message: {final_error}")
            try:
                await loading_msg.edit_text(f"⚠️ Process completed but status update failed: {str(final_error)}")
            except:
                pass

    except Exception as main_error:
        error_text = f"❌ Critical error in recent files process: {str(main_error)}"
        print(f"CRITICAL ERROR: Recent files process failed: {main_error}")

        try:
            if loading_msg:
                await loading_msg.edit_text(error_text)
            else:
                await message.reply_text(error_text)
        except Exception as msg_error:
            print(f"ERROR: Could not send error message: {msg_error}")

async def handle_popular_files_direct(client: Client, message: Message, is_callback: bool = False):
    """Get and send 5 popular files directly to user, with different files each time"""
    loading_msg = None

    try:
        user_id = message.from_user.id if message.from_user else message.chat.id

        # Initialize loading message
        if is_callback:
            loading_msg = await message.edit_text("🔥 Getting popular files...")
        else:
            loading_msg = await message.reply_text("🔥 Getting popular files...")

        print(f"DEBUG: Starting popular files retrieval for user {user_id}")

        # Get current offset for this user (defaults to 0)
        current_offset = user_popular_offsets.get(user_id, 0)
        print(f"DEBUG: Current offset for user {user_id}: {current_offset}")

        # Step 1: Query MongoDB for popular file metadata with offset
        try:
            results = await get_popular_files(limit=10, offset=current_offset)  # Get more to account for invalid files
            print(f"DEBUG: Retrieved {len(results)} popular files from database with offset {current_offset}")
        except Exception as db_error:
            error_msg = f"❌ Database query failed: {str(db_error)}"
            print(f"ERROR: MongoDB query failed: {db_error}")
            await loading_msg.edit_text(error_msg)
            return

        if not results:
            # Reset offset if no more files and try again
            if current_offset > 0:
                user_popular_offsets[user_id] = 0
                results = await get_popular_files(limit=10, offset=0)
                print(f"DEBUG: Reset offset, retrieved {len(results)} files")

            if not results:
                await loading_msg.edit_text("❌ No popular files found in database.")
                return

        try:
            await loading_msg.edit_text(f"📁 Processing {len(results)} popular files...")
        except Exception as msg_error:
            print(f"WARNING: Failed to update loading message: {msg_error}")

        # Step 2: Send 5 popular files directly to user
        sent_count = 0
        target_count = 5  # Target number of files to send
        errors_encountered = []

        for idx, file_data in enumerate(results):
            if sent_count >= target_count:
                print(f"DEBUG: Reached target count of {target_count} files")
                break

            print(f"DEBUG: Processing popular file {idx + 1}/{len(results)}")

            try:
                # Extract metadata from MongoDB document with validation
                if not isinstance(file_data, dict):
                    print(f"ERROR: Invalid file_data type: {type(file_data)}")
                    errors_encountered.append(f"Invalid data structure for file {idx + 1}")
                    continue

                file_id = str(file_data.get('_id', ''))
                file_name = file_data.get('file_name', 'Unknown File')
                file_type = file_data.get('file_type', 'unknown')
                access_count = file_data.get('access_count', 0)

                if not file_id:
                    print(f"ERROR: No file_id found for file: {file_name}")
                    errors_encountered.append(f"Missing file_id for {file_name}")
                    continue

                print(f"DEBUG: Processing popular file: {file_name} with ID: {file_id}, Type: {file_type}, Views: {access_count}")

                # Parse file_id to extract message_id
                message_id = None
                try:
                    if '_' in file_id:
                        parts = file_id.split('_')
                        if len(parts) >= 2:
                            message_id = int(parts[-1])
                            print(f"DEBUG: Extracted message_id {message_id} from composite ID: {file_id}")
                        else:
                            print(f"ERROR: Invalid composite file_id format: {file_id}")
                            errors_encountered.append(f"Invalid ID format: {file_id}")
                            continue
                    else:
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

                # Retrieve file from Telegram
                try:
                    print(f"DEBUG: Fetching message {message_id} from channel {Config.INDEX_CHANNEL_ID}")
                    db_message = await client.get_messages(Config.INDEX_CHANNEL_ID, message_id)

                    if not db_message or db_message.empty or not db_message.media:
                        print(f"ERROR: Message {message_id} invalid or has no media")
                        errors_encountered.append(f"Message {message_id} invalid or no media")
                        continue

                    print(f"DEBUG: Successfully retrieved message {message_id} with media")

                except Exception as telegram_get_error:
                    print(f"ERROR: Telegram get_messages failed for message {message_id}: {telegram_get_error}")
                    errors_encountered.append(f"Get message {message_id}: {str(telegram_get_error)}")
                    continue

                # Send the file to user without caption but with custom keyboard
                try:
                    print(f"DEBUG: Sending popular media from message {message_id} to user {message.chat.id}")

                    # Create custom keyboard
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

                    # Send media based on type without caption
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
                        copied_msg = await db_message.copy(
                            chat_id=message.chat.id,
                            reply_markup=custom_keyboard,
                            protect_content=Config.PROTECT_CONTENT
                        )

                    if copied_msg:
                        sent_count += 1
                        print(f"SUCCESS: Sent popular file #{sent_count}: {file_name}")

                        # Increment access count
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

        # Update offset for next time (increment by files processed)
        user_popular_offsets[user_id] = current_offset + len(results)
        print(f"DEBUG: Updated offset for user {user_id} to {user_popular_offsets[user_id]}")

        # Send final status with navigation buttons
        try:
            if sent_count > 0:
                final_text = f"✅ Successfully sent {sent_count} popular files!"
                if errors_encountered:
                    final_text += f"\n\n⚠️ {len(errors_encountered)} files had issues (check logs)"
            else:
                final_text = "❌ No valid popular files could be sent."
                if errors_encountered:
                    final_text += f"\n\nErrors encountered:\n• " + "\n• ".join(errors_encountered[:3])
                    if len(errors_encountered) > 3:
                        final_text += f"\n• ... and {len(errors_encountered) - 3} more"

            nav_buttons = [
                InlineKeyboardButton("🔥 More Popular", callback_data="rand_popular"),
                InlineKeyboardButton("🎲 Random", callback_data="rand_new")
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

            print(f"DEBUG: Popular files final status - Sent: {sent_count}, Errors: {len(errors_encountered)}")

        except Exception as final_error:
            print(f"ERROR: Failed to send final status message: {final_error}")
            try:
                await loading_msg.edit_text(f"⚠️ Process completed but status update failed: {str(final_error)}")
            except:
                pass

    except Exception as main_error:
        error_text = f"❌ Critical error in popular files process: {str(main_error)}"
        print(f"CRITICAL ERROR: Popular files process failed: {main_error}")

        try:
            if loading_msg:
                await loading_msg.edit_text(error_text)
            else:
                await message.reply_text(error_text)
        except Exception as msg_error:
            print(f"ERROR: Could not send error message: {msg_error}")

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
        if not await use_command(user_id):
            needs_verification, remaining = await check_command_limit(user_id)

            # Create verification button
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ])

            await message.reply_text(
                f"⚠️ **Command Limit Reached!**\n\n"
                f"You've used all your free commands (3/3).\n\n"
                f"🔓 **Get instant access by:**\n"
                f"• Getting a verification token (with ads)\n"
                f"• Upgrading to Premium (no ads)\n\n"
                f"💡 Premium users get unlimited access without verification!",
                reply_markup=buttons
            )
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
        if not await use_command(user_id):
            needs_verification, remaining = await check_command_limit(user_id)

            # Create verification button
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Get Access Token", callback_data="get_token")],
                [InlineKeyboardButton("💎 Remove Ads - Buy Premium", callback_data="show_premium_plans")]
            ])

            await message.reply_text(
                f"⚠️ **Command Limit Reached!**\n\n"
                f"You've used all your free commands (3/3).\n\n"
                f"🔓 **Get instant access by:**\n"
                f"• Getting a verification token (with ads)\n"
                f"• Upgrading to Premium (no ads)\n\n"
                f"💡 Premium users get unlimited access without verification!",
                reply_markup=buttons
            )
            return

        await handle_recent_files_direct(client, message, is_callback=False)
    except Exception as e:
        print(f"Error in recent_files_command: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")
# Mother bot search.py - File features disabled
# All file features (random, recent, popular) are only available in clone bots

@Client.on_message(filters.command(["rand", "random", "recent", "popular", "search"]) & filters.private)
async def disabled_file_commands(client: Client, message: Message):
    """Redirect users to create clone for file features"""
    user_id = message.from_user.id
    command = message.command[0]

    # Detect if this is mother bot
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    is_clone_bot = hasattr(client, 'is_clone') and client.is_clone

    # Additional checks for clone bot detection
    if not is_clone_bot:
        is_clone_bot = (
            bot_token != Config.BOT_TOKEN or
            hasattr(client, 'clone_config') and client.clone_config or
            hasattr(client, 'clone_data')
        )

    # Only show this message in mother bot
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
async def disabled_keyboard_handlers(client: Client, message: Message):
    """Handle disabled keyboard buttons for file features"""
    button_text = message.text

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