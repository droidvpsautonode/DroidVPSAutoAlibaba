"""
Logs handler module.
Displays action logs from the database.
"""

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from app.auth import owner_only
from app.db import db
from app.keyboards import main_menu_keyboard
from app.states import CB_LOGS, CB_HOME
from app.utils import get_home_keyboard


# Status emoji mapping
STATUS_EMOJI = {
    "success": "✅",
    "failed": "❌",
    "pending": "⏳",
}


@owner_only
async def cb_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show recent action logs via callback."""
    query = update.callback_query
    await query.answer()

    logs = db.get_logs(limit=20)
    text = _format_logs(logs)

    await query.edit_message_text(
        text,
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )


@owner_only
async def cmd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /logs command."""
    logs = db.get_logs(limit=20)
    text = _format_logs(logs)

    await update.message.reply_text(
        text,
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )


def _format_logs(logs: list[dict]) -> str:
    """Format log entries into readable text."""
    if not logs:
        return (
            "<b>📜 Log Aksi</b>\n\n"
            "Belum ada log tercatat."
        )

    text = "<b>📜 Log Aksi (20 Terakhir)</b>\n"
    text += f"{'━' * 28}\n\n"

    for log in logs:
        status_icon = STATUS_EMOJI.get(log["status"], "⚪")
        timestamp = log["timestamp"][:16]  # Trim seconds
        action = log["action"].replace("_", " ").title()
        account = log.get("account_name", "") or "-"
        instance = log.get("instance_id", "") or "-"
        region = log.get("region_id", "") or "-"

        text += (
            f"{status_icon} <b>{action}</b>\n"
            f"   📅 {timestamp}\n"
            f"   📌 Akun: {account}\n"
        )

        if region != "-":
            text += f"   🌏 Region: {region}\n"
        if instance != "-":
            text += f"   🖥 Instance: <code>{instance}</code>\n"
        if log["status"] == "failed" and log.get("error_message"):
            error_short = log["error_message"][:80]
            text += f"   ⚠️ Error: {error_short}\n"

        text += "\n"

    return text


# ==================== HANDLER REGISTRATION ====================

def get_logs_handlers() -> list:
    """Get all handlers for logs module."""
    return [
        CommandHandler("logs", cmd_logs),
        CallbackQueryHandler(cb_logs, pattern=f"^{CB_LOGS}$"),
    ]
