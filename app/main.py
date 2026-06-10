"""
Main entry point for the Alibaba Cloud ECS Telegram Bot.
Registers all handlers and starts the bot.
"""

import logging
import sys

from telegram.ext import Application

from app.config import Config
from app.handlers.start import get_start_handlers
from app.handlers.accounts import get_accounts_handlers, get_add_account_conversation
from app.handlers.regions import get_regions_handlers
from app.handlers.instances import get_instances_handlers
from app.handlers.actions import (
    get_actions_handlers,
    get_reset_password_conversation,
    get_delete_instance_conversation,
    get_reinstall_conversation,
    get_open_all_conversation,
)
from app.handlers.logs import get_logs_handlers

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    """Initialize and run the bot."""
    # Validate config
    errors = Config.validate()
    if errors:
        for error in errors:
            logger.error(f"Config Error: {error}")
        sys.exit(1)

    logger.info("Starting Alibaba Cloud ECS Telegram Bot...")
    logger.info(f"Owner IDs: {Config.OWNER_IDS}")

    # Build application
    application = (
        Application.builder()
        .token(Config.TELEGRAM_BOT_TOKEN)
        .build()
    )

    # ==================== Register Handlers ====================
    # Order matters! ConversationHandlers must be registered BEFORE
    # generic CallbackQueryHandlers to avoid conflicts.

    # 1. Conversation Handlers (multi-step flows)
    application.add_handler(get_add_account_conversation())
    application.add_handler(get_reset_password_conversation())
    application.add_handler(get_delete_instance_conversation())
    application.add_handler(get_reinstall_conversation())
    application.add_handler(get_open_all_conversation())

    # 2. Start/Navigation handlers
    for handler in get_start_handlers():
        application.add_handler(handler)

    # 3. Account handlers
    for handler in get_accounts_handlers():
        application.add_handler(handler)

    # 4. Region handlers
    for handler in get_regions_handlers():
        application.add_handler(handler)

    # 5. Instance handlers
    for handler in get_instances_handlers():
        application.add_handler(handler)

    # 6. Action handlers (non-conversation)
    for handler in get_actions_handlers():
        application.add_handler(handler)

    # 7. Log handlers
    for handler in get_logs_handlers():
        application.add_handler(handler)

    # ==================== Start Bot ====================
    logger.info("Bot is running. Press Ctrl+C to stop.")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
