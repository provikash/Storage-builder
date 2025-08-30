
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils.error_handler import safe_edit_message
from info import Config

@Client.on_callback_query(filters.regex("^about_water$"))
async def about_water_callback(client: Client, query: CallbackQuery):
    """Show water-related about information"""
    await query.answer()

    # Check if this is clone bot or mother bot
    bot_token = getattr(client, 'bot_token', Config.BOT_TOKEN)
    is_clone_bot = bot_token != Config.BOT_TOKEN

    if is_clone_bot:
        # Clone bot water information
        text = f"💧 **About WaterFlow Clone Bot**\n\n"
        text += f"🌊 **Pure File Streaming Technology**\n"
        text += f"Like water flowing through channels, your files move seamlessly through our secure network.\n\n"
        text += f"💧 **Water-Inspired Features:**\n"
        text += f"• 🌊 **Fluid File Sharing** - Smooth as water\n"
        text += f"• 💎 **Crystal Clear** - Transparent operations\n"
        text += f"• 🔄 **Continuous Flow** - Never-ending service\n"
        text += f"• 🏔️ **Pure & Clean** - No ads, no clutter\n"
        text += f"• 🌀 **Adaptive Stream** - Adjusts to your needs\n\n"
        text += f"🔮 **Like a drop in the ocean, every file matters.**\n\n"
        text += f"🌐 **Clone Bot Technology**\n"
        text += f"This personal clone brings the power of water to your fingertips - "
        text += f"pure, essential, and life-giving file management."
    else:
        # Mother bot water information
        text = f"💧 **About AquaCore Mother Bot**\n\n"
        text += f"🌊 **The Source of All Streams**\n"
        text += f"Like a mighty river feeding countless streams, this Mother Bot powers an entire network of clone bots.\n\n"
        text += f"💧 **Water Cycle Technology:**\n"
        text += f"• ☁️ **Evaporation** - Your files rise to the cloud\n"
        text += f"• 🌧️ **Precipitation** - Data flows to clone networks\n"
        text += f"• 🏔️ **Collection** - Files gather in secure reservoirs\n"
        text += f"• 🌊 **Distribution** - Streams reach every user\n\n"
        text += f"🔋 **Hydro-Powered Features:**\n"
        text += f"• 🤖 **Clone Generation** - Birth new bot streams\n"
        text += f"• 💎 **Premium Aquifers** - Deep feature wells\n"
        text += f"• 🔐 **Water-tight Security** - No leaks, ever\n"
        text += f"• 📊 **Flow Analytics** - Monitor every drop\n\n"
        text += f"🌍 **Sustaining Digital Life**\n"
        text += f"Just as water is essential for life, this bot system is essential for your digital file ecosystem."

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🌊 Water Facts", callback_data="water_facts"),
            InlineKeyboardButton("💧 Tech Details", callback_data="water_tech")
        ],
        [InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_start")]
    ])

    await safe_edit_message(query, text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^water_facts$"))
async def water_facts_callback(client: Client, query: CallbackQuery):
    """Show interesting water facts"""
    await query.answer()

    text = f"🌊 **Amazing Water Facts**\n\n"
    text += f"💧 **Did You Know?**\n"
    text += f"• Earth is 71% water, just like this bot covers 71% of your file needs\n"
    text += f"• Water can exist in 3 states - like our bot's flexible deployment\n"
    text += f"• The human body is 60% water - essential for life\n"
    text += f"• Water has no taste, smell, or color - pure like our code\n"
    text += f"• Water freezes at 0°C and boils at 100°C\n"
    text += f"• A water molecule contains 2 hydrogen and 1 oxygen atom\n\n"
    text += f"🔬 **Water & Technology:**\n"
    text += f"• Data flows like water through networks\n"
    text += f"• Cloud computing mimics the water cycle\n"
    text += f"• Streaming services are named after water flow\n"
    text += f"• Server cooling requires massive amounts of water\n\n"
    text += f"🌍 **Water Conservation:**\n"
    text += f"Just as we optimize code, we should conserve water for future generations."

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("💧 Back to About", callback_data="about_water")]
    ])

    await safe_edit_message(query, text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^water_tech$"))
async def water_tech_callback(client: Client, query: CallbackQuery):
    """Show water technology information"""
    await query.answer()

    text = f"💧 **Water Technology Integration**\n\n"
    text += f"🔬 **Hydro-Inspired Bot Architecture:**\n"
    text += f"• **Flow Control** - Like water pressure regulation\n"
    text += f"• **Stream Processing** - Continuous data flow\n"
    text += f"• **Filtration System** - Clean, secure file processing\n"
    text += f"• **Reservoir Storage** - Massive file capacity\n"
    text += f"• **Distribution Network** - Global clone deployment\n\n"
    text += f"⚡ **Liquid Computing Principles:**\n"
    text += f"• **Fluidity** - Seamless user experience\n"
    text += f"• **Transparency** - Clear operations and pricing\n"
    text += f"• **Adaptability** - Shapes to user needs\n"
    text += f"• **Purity** - No malicious code or tracking\n\n"
    text += f"🌐 **Digital Water Cycle:**\n"
    text += f"1. **Upload** (Evaporation) - Files rise to our servers\n"
    text += f"2. **Process** (Condensation) - Data organizing and indexing\n"
    text += f"3. **Share** (Precipitation) - Files rain down to users\n"
    text += f"4. **Archive** (Collection) - Stored in digital reservoirs"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("💧 Back to About", callback_data="about_water")]
    ])

    await safe_edit_message(query, text, reply_markup=buttons)
