"""
Authentication module.
Owner-only access control for the Telegram bot.
"""

from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

from app.config import Config


def is_owner(user_id: int) -> bool:
    """Check if a Telegram user ID is in the owner list."""
    return user_id in Config.OWNER_IDS


def owner_only(func):
    """
    Decorator for handler functions.
    Only allows execution if the user is an owner.
    Non-owners receive 'Unauthorized.' or are ignored.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = None

        if update.effective_user:
            user_id = update.effective_user.id

        if user_id is None or not is_owner(user_id):
            # Reply unauthorized for direct messages
            if update.message:
                await update.message.reply_text("⛔ Unauthorized.")
            elif update.callback_query:
                await update.callback_query.answer("⛔ Unauthorized.", show_alert=True)
            return

        return await func(update, context, *args, **kwargs)

    return wrapper


def owner_only_callback(func):
    """
    Decorator specifically for callback query handlers.
    Answers the callback and shows alert if unauthorized.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = None

        if update.effective_user:
            user_id = update.effective_user.id

        if user_id is None or not is_owner(user_id):
            if update.callback_query:
                await update.callback_query.answer(
                    "⛔ Unauthorized.", show_alert=True
                )
            return

        return await func(update, context, *args, **kwargs)

    return wrapper
