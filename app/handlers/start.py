"""
Start handler module.
Handles /start, /help, main menu, and navigation callbacks.
"""

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from app.auth import owner_only
from app.keyboards import main_menu_keyboard
from app.states import CB_HOME, CB_HELP, CB_CANCEL
from app.utils import clear_user_data


WELCOME_TEXT = """
<b>🚀 Alibaba Cloud ECS Manager</b>

Selamat datang! Bot ini membantu Anda mengelola instance ECS/VPS/RDP di Alibaba Cloud.

<b>Fitur utama:</b>
• Multi-akun Alibaba Cloud
• Auto-detect region aktif
• Kelola instance (start/stop/reboot)
• Reset password instance
• Reinstall OS / Ganti system disk
• Security group (open/close all ports)
• Logging semua aksi

Pilih menu di bawah untuk memulai:
"""

HELP_TEXT = """
<b>❓ Bantuan - Alibaba Cloud ECS Manager</b>

<b>📋 Command yang tersedia:</b>
• /start - Menu utama
• /help - Tampilkan bantuan ini
• /accounts - Daftar akun Alibaba
• /scan - Scan region aktif
• /instances - Daftar instance
• /logs - Lihat log aksi
• /cancel - Batalkan input aktif

<b>🔄 Alur penggunaan:</b>
1. Tambah akun Alibaba (AccessKey)
2. Pilih akun yang ingin dikelola
3. Scan region untuk menemukan instance
4. Pilih region → pilih instance
5. Lakukan aksi (reboot, start, stop, dll)

<b>🔐 Keamanan:</b>
• AccessKey Secret dienkripsi di database
• Bot hanya merespons owner yang terdaftar
• Aksi berbahaya memerlukan konfirmasi ganda
• Password baru tidak disimpan di log

<b>⚠️ Peringatan Open All Ports:</b>
Fitur "Open All TCP/UDP Ports" membuka port 1-65535 ke seluruh internet (0.0.0.0/0). Gunakan dengan bijak dan hanya jika Anda memahami risikonya.

<b>📝 Catatan:</b>
• Gunakan RAM user dengan permission AliyunECSFullAccess
• Jangan gunakan AccessKey root account
• Backup data sebelum reinstall OS
"""


@owner_only
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    clear_user_data(context)
    await update.message.reply_text(
        WELCOME_TEXT,
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )


@owner_only
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await update.message.reply_text(
        HELP_TEXT,
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )


@owner_only
async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cancel command - cancel current operation."""
    clear_user_data(context)
    await update.message.reply_text(
        "❌ Operasi dibatalkan.\n\nKembali ke menu utama:",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )


@owner_only
async def cb_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Home button callback - return to main menu."""
    query = update.callback_query
    await query.answer()
    clear_user_data(context)
    await query.edit_message_text(
        WELCOME_TEXT,
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )


@owner_only
async def cb_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Help button callback."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        HELP_TEXT,
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )


@owner_only
async def cb_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Cancel button callback."""
    query = update.callback_query
    await query.answer()
    clear_user_data(context)
    await query.edit_message_text(
        "❌ Operasi dibatalkan.\n\nKembali ke menu utama:",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )


def get_start_handlers() -> list:
    """Get all handlers for this module."""
    return [
        CommandHandler("start", cmd_start),
        CommandHandler("help", cmd_help),
        CommandHandler("cancel", cmd_cancel),
        CallbackQueryHandler(cb_home, pattern=f"^{CB_HOME}$"),
        CallbackQueryHandler(cb_help, pattern=f"^{CB_HELP}$"),
        CallbackQueryHandler(cb_cancel, pattern=f"^{CB_CANCEL}$"),
    ]
