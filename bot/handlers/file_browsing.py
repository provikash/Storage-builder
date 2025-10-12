
"""
File browsing callback handlers (random, recent, popular files)
"""
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from bot.utils.ui_builders import build_feature_disabled_message, build_mother_bot_feature_message, CALLBACK_DATA
from bot.utils.callback_error_handler import safe_callback_handler
from bot.utils.permissions import is_clone_bot_instance
from bot.logging import LOGGER

logger = LOGGER(__name__)

@Client.on_callback_query(filters.regex("^(random_files|popular_files)$"), group=4)
@safe_callback_handler
async def file_browsing_callback_handler(client: Client, query: CallbackQuery):
    """Handle file browsing callbacks with proper routing"""
    user_id = query.from_user.id
    callback_data = query.data
    
    logger.info(f"📁 File browsing callback: {callback_data} from user {user_id}")
    
    await query.answer()
    
    is_clone, bot_token = is_clone_bot_instance(client)
    
    # Check if this is mother bot
    if not is_clone:
        feature_name = callback_data.replace('_files', '').replace('_', ' ').title()
        message_text = build_mother_bot_feature_message(f"{feature_name} Files")
        await query.edit_message_text(message_text)
        return
        
    # Get clone data to check feature status
    from bot.database.clone_db import get_clone_by_bot_token
    clone_data = await get_clone_by_bot_token(bot_token)
    
    if not clone_data:
        await query.edit_message_text("❌ Clone configuration not found!")
        return
        
    # Check feature enablement with proper defaults
    feature_enabled = True
    feature_display_name = ""
    
    if callback_data == CALLBACK_DATA['RANDOM_FILES']:
        feature_enabled = clone_data.get('random_mode', True)
        feature_display_name = "Random Files"
    elif callback_data == CALLBACK_DATA['POPULAR_FILES']:
        feature_enabled = clone_data.get('popular_mode', True)
        feature_display_name = "Popular Files"
        
    if not feature_enabled:
        text, buttons = build_feature_disabled_message(feature_display_name)
        await query.edit_message_text(text, reply_markup=buttons)
        return
        
    # Route to clone file handlers
    try:
        if callback_data == CALLBACK_DATA['RANDOM_FILES']:
            from bot.plugins.clone_random_files import handle_clone_random_files
            await handle_clone_random_files(client, query)
        elif callback_data == CALLBACK_DATA['POPULAR_FILES']:
            from bot.plugins.clone_random_files import handle_clone_popular_files
            await handle_clone_popular_files(client, query)
    except Exception as handler_error:
        logger.error(f"Error in {callback_data} handler: {handler_error}")
        await query.edit_message_text(f"❌ Error loading {feature_display_name.lower()}. Please try again.")
