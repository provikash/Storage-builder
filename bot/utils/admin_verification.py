
def admin_required(func):
    """Simple admin verification decorator"""
    async def wrapper(client, message):
        user_id = message.from_user.id
        if user_id not in Config.ADMINS and user_id != Config.OWNER_ID:
            return await message.reply_text("❌ This command is only available to administrators.")
        return await func(client, message)
    return wrapper
