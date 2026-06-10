"""
Accounts handler module.
Handles add, list, delete, and select Alibaba Cloud accounts.
Uses ConversationHandler for multi-step add account flow.
"""

from telegram import Update
from telegram.ext import (
    ContextTypes, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters,
)

from app.auth import owner_only
from app.db import db
from app.security import security
from app.keyboards import (
    main_menu_keyboard, accounts_list_keyboard,
    accounts_delete_keyboard, account_delete_confirm_keyboard,
    back_home_keyboard, cancel_keyboard,
)
from app.states import (
    CB_ACCOUNTS_LIST, CB_ACCOUNT_SELECT, CB_ACCOUNT_ADD,
    CB_ACCOUNT_DELETE, CB_ACCOUNT_DELETE_YES, CB_HOME, CB_CANCEL,
    STATE_ADD_ACCOUNT_NAME, STATE_ADD_ACCOUNT_KEY_ID,
    STATE_ADD_ACCOUNT_KEY_SECRET, STATE_ADD_ACCOUNT_NOTES,
)
from app.utils import (
    show_loading, show_success, show_error,
    set_user_data, get_user_data,
    CTX_CURRENT_ACCOUNT_ID, CTX_CURRENT_ACCOUNT_NAME,
    CTX_TEMP_ACCOUNT_NAME, CTX_TEMP_KEY_ID, CTX_TEMP_KEY_SECRET,
    get_home_keyboard,
)


# ==================== LIST ACCOUNTS ====================

@owner_only
async def cb_accounts_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of Alibaba Cloud accounts."""
    query = update.callback_query
    await query.answer()

    accounts = db.get_accounts()
    if not accounts:
        await query.edit_message_text(
            "<b>🧭 Daftar Akun Alibaba Cloud</b>\n\n"
            "Belum ada akun terdaftar.\n"
            "Gunakan menu <b>➕ Tambah Akun</b> untuk menambahkan akun baru.",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
        return

    # Build account list text
    text = "<b>🧭 Pilih Akun Alibaba Cloud</b>\n\n"
    for acc in accounts:
        masked_key = security.mask_access_key_id(acc["access_key_id"])
        text += f"• <b>{acc['account_name']}</b> ({masked_key})\n"
    text += "\nPilih akun untuk mengelola instance:"

    await query.edit_message_text(
        text,
        reply_markup=accounts_list_keyboard(accounts),
        parse_mode="HTML"
    )


@owner_only
async def cmd_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /accounts command."""
    accounts = db.get_accounts()
    if not accounts:
        await update.message.reply_text(
            "<b>🧭 Daftar Akun Alibaba Cloud</b>\n\n"
            "Belum ada akun terdaftar.\n"
            "Gunakan menu <b>➕ Tambah Akun</b> untuk menambahkan akun baru.",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
        return

    text = "<b>🧭 Pilih Akun Alibaba Cloud</b>\n\n"
    for acc in accounts:
        masked_key = security.mask_access_key_id(acc["access_key_id"])
        text += f"• <b>{acc['account_name']}</b> ({masked_key})\n"
    text += "\nPilih akun untuk mengelola instance:"

    await update.message.reply_text(
        text,
        reply_markup=accounts_list_keyboard(accounts),
        parse_mode="HTML"
    )


# ==================== SELECT ACCOUNT ====================

@owner_only
async def cb_account_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle account selection."""
    query = update.callback_query
    await query.answer()

    # Extract account ID from callback data
    account_id = int(query.data.replace(CB_ACCOUNT_SELECT, ""))
    account = db.get_account_by_id(account_id)

    if not account:
        await show_error(query, "Akun tidak ditemukan.")
        return

    # Store selected account in context
    set_user_data(context, CTX_CURRENT_ACCOUNT_ID, account_id)
    set_user_data(context, CTX_CURRENT_ACCOUNT_NAME, account["account_name"])

    masked_key = security.mask_access_key_id(account["access_key_id"])
    text = (
        f"<b>✅ Akun Terpilih</b>\n\n"
        f"📌 <b>Nama:</b> {account['account_name']}\n"
        f"🔑 <b>AccessKey:</b> {masked_key}\n"
        f"📅 <b>Ditambahkan:</b> {account['created_at']}\n"
    )
    if account.get("notes"):
        text += f"📝 <b>Catatan:</b> {account['notes']}\n"

    text += "\nPilih aksi selanjutnya:"

    from app.keyboards import InlineKeyboardMarkup, InlineKeyboardButton
    from app.states import CB_REGIONS_SCAN, CB_HOME

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Scan Region", callback_data=CB_REGIONS_SCAN)],
        [InlineKeyboardButton("🌏 Lihat Cache Region", callback_data="regions_cached")],
        [InlineKeyboardButton("🏠 Home", callback_data=CB_HOME)],
    ])

    await query.edit_message_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# ==================== DELETE ACCOUNT ====================

@owner_only
async def cb_accounts_delete_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of accounts available for deletion."""
    query = update.callback_query
    await query.answer()

    accounts = db.get_accounts()
    if not accounts:
        await query.edit_message_text(
            "<b>🗑 Hapus Akun</b>\n\nBelum ada akun terdaftar.",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
        return

    text = "<b>🗑 Pilih Akun untuk Dihapus</b>\n\n⚠️ Akun yang dihapus tidak bisa dikembalikan.\n"
    await query.edit_message_text(
        text,
        reply_markup=accounts_delete_keyboard(accounts),
        parse_mode="HTML"
    )


@owner_only
async def cb_account_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm account deletion."""
    query = update.callback_query
    await query.answer()

    account_id = int(query.data.replace(CB_ACCOUNT_DELETE, ""))
    account = db.get_account_by_id(account_id)

    if not account:
        await show_error(query, "Akun tidak ditemukan.")
        return

    text = (
        f"<b>⚠️ Konfirmasi Hapus Akun</b>\n\n"
        f"Anda yakin ingin menghapus akun:\n"
        f"• <b>{account['account_name']}</b>\n"
        f"• {security.mask_access_key_id(account['access_key_id'])}\n\n"
        f"Semua cache region untuk akun ini juga akan dihapus."
    )

    await query.edit_message_text(
        text,
        reply_markup=account_delete_confirm_keyboard(account_id),
        parse_mode="HTML"
    )


@owner_only
async def cb_account_delete_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute account deletion."""
    query = update.callback_query
    await query.answer()

    account_id = int(query.data.replace(CB_ACCOUNT_DELETE_YES, ""))
    account = db.get_account_by_id(account_id)

    if not account:
        await show_error(query, "Akun tidak ditemukan.")
        return

    await show_loading(query, "⏳ Menghapus akun...")

    try:
        db.delete_account(account_id)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="delete_account",
            account_name=account["account_name"],
            status="success"
        )
        await show_success(
            query,
            f"Akun <b>{account['account_name']}</b> berhasil dihapus.",
            get_home_keyboard()
        )
    except Exception as e:
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="delete_account",
            account_name=account["account_name"],
            status="failed",
            error_message=str(e)
        )
        await show_error(query, f"Gagal menghapus akun: {e}")


# ==================== ADD ACCOUNT (ConversationHandler) ====================

@owner_only
async def cb_account_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start add account conversation."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "<b>➕ Tambah Akun Alibaba Cloud</b>\n\n"
        "Langkah 1/4: Masukkan <b>nama akun</b> (untuk identifikasi).\n\n"
        "Contoh: <code>akun-produksi</code>, <code>vps-singapura</code>\n\n"
        "Ketik /cancel untuk membatalkan.",
        parse_mode="HTML"
    )
    return STATE_ADD_ACCOUNT_NAME


@owner_only
async def add_account_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive account name."""
    account_name = update.message.text.strip()

    # Validate
    if len(account_name) < 2 or len(account_name) > 50:
        await update.message.reply_text(
            "❌ Nama akun harus 2-50 karakter. Coba lagi:",
            parse_mode="HTML"
        )
        return STATE_ADD_ACCOUNT_NAME

    if db.account_exists(account_name):
        await update.message.reply_text(
            f"❌ Nama akun <b>{account_name}</b> sudah digunakan. Pilih nama lain:",
            parse_mode="HTML"
        )
        return STATE_ADD_ACCOUNT_NAME

    set_user_data(context, CTX_TEMP_ACCOUNT_NAME, account_name)

    await update.message.reply_text(
        f"✅ Nama: <b>{account_name}</b>\n\n"
        "Langkah 2/4: Masukkan <b>AccessKey ID</b>.\n\n"
        "⚠️ Pesan yang berisi AccessKey akan dihapus otomatis untuk keamanan.\n\n"
        "Ketik /cancel untuk membatalkan.",
        parse_mode="HTML"
    )
    return STATE_ADD_ACCOUNT_KEY_ID


@owner_only
async def add_account_key_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive AccessKey ID."""
    key_id = update.message.text.strip()

    # Try to delete the message containing the key
    try:
        await update.message.delete()
    except Exception:
        pass  # May fail if bot doesn't have delete permission

    # Validate
    if len(key_id) < 10:
        await update.message.reply_text(
            "❌ AccessKey ID terlalu pendek. Coba lagi:",
            parse_mode="HTML"
        )
        return STATE_ADD_ACCOUNT_KEY_ID

    set_user_data(context, CTX_TEMP_KEY_ID, key_id)
    masked = security.mask_access_key_id(key_id)

    await update.effective_chat.send_message(
        f"✅ AccessKey ID: <b>{masked}</b>\n\n"
        "Langkah 3/4: Masukkan <b>AccessKey Secret</b>.\n\n"
        "⚠️ Pesan akan dihapus otomatis. Secret disimpan terenkripsi.\n\n"
        "Ketik /cancel untuk membatalkan.",
        parse_mode="HTML"
    )
    return STATE_ADD_ACCOUNT_KEY_SECRET


@owner_only
async def add_account_key_secret(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive AccessKey Secret."""
    key_secret = update.message.text.strip()

    # Try to delete the message containing the secret
    try:
        await update.message.delete()
    except Exception:
        pass  # May fail if bot doesn't have delete permission

    # Validate
    if len(key_secret) < 10:
        await update.effective_chat.send_message(
            "❌ AccessKey Secret terlalu pendek. Coba lagi:",
            parse_mode="HTML"
        )
        return STATE_ADD_ACCOUNT_KEY_SECRET

    set_user_data(context, CTX_TEMP_KEY_SECRET, key_secret)

    await update.effective_chat.send_message(
        "✅ AccessKey Secret diterima (terenkripsi).\n\n"
        "Langkah 4/4: Masukkan <b>catatan</b> (opsional).\n\n"
        "Contoh: <code>VPS Singapore untuk testing</code>\n"
        "Ketik <code>-</code> untuk skip.\n\n"
        "Ketik /cancel untuk membatalkan.",
        parse_mode="HTML"
    )
    return STATE_ADD_ACCOUNT_NOTES


@owner_only
async def add_account_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive notes and save account."""
    notes = update.message.text.strip()
    if notes == "-":
        notes = ""

    account_name = get_user_data(context, CTX_TEMP_ACCOUNT_NAME)
    key_id = get_user_data(context, CTX_TEMP_KEY_ID)
    key_secret = get_user_data(context, CTX_TEMP_KEY_SECRET)

    if not account_name or not key_id or not key_secret:
        await update.message.reply_text(
            "❌ Data tidak lengkap. Silakan mulai ulang dengan /start.",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
        return ConversationHandler.END

    # Encrypt the secret
    encrypted_secret = security.encrypt(key_secret)

    # Save to database
    try:
        db.add_account(
            account_name=account_name,
            access_key_id=key_id,
            access_key_secret_encrypted=encrypted_secret,
            notes=notes,
        )
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="add_account",
            account_name=account_name,
            status="success"
        )

        masked_key = security.mask_access_key_id(key_id)
        await update.message.reply_text(
            f"<b>✅ Akun Berhasil Ditambahkan!</b>\n\n"
            f"📌 <b>Nama:</b> {account_name}\n"
            f"🔑 <b>AccessKey:</b> {masked_key}\n"
            f"📝 <b>Catatan:</b> {notes or '-'}\n\n"
            f"Gunakan menu <b>🧭 Pilih Akun</b> untuk mulai mengelola.",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="add_account",
            account_name=account_name,
            status="failed",
            error_message=str(e)
        )
        await update.message.reply_text(
            f"❌ Gagal menyimpan akun: {e}",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )

    # Clear temp data
    context.user_data.pop(CTX_TEMP_ACCOUNT_NAME, None)
    context.user_data.pop(CTX_TEMP_KEY_ID, None)
    context.user_data.pop(CTX_TEMP_KEY_SECRET, None)

    return ConversationHandler.END


async def add_account_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel add account conversation."""
    context.user_data.pop(CTX_TEMP_ACCOUNT_NAME, None)
    context.user_data.pop(CTX_TEMP_KEY_ID, None)
    context.user_data.pop(CTX_TEMP_KEY_SECRET, None)

    await update.message.reply_text(
        "❌ Penambahan akun dibatalkan.",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )
    return ConversationHandler.END


# ==================== HANDLER REGISTRATION ====================

def get_add_account_conversation() -> ConversationHandler:
    """Get ConversationHandler for adding accounts."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cb_account_add_start, pattern=f"^{CB_ACCOUNT_ADD}$"),
        ],
        states={
            STATE_ADD_ACCOUNT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_account_name),
            ],
            STATE_ADD_ACCOUNT_KEY_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_account_key_id),
            ],
            STATE_ADD_ACCOUNT_KEY_SECRET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_account_key_secret),
            ],
            STATE_ADD_ACCOUNT_NOTES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_account_notes),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", add_account_cancel),
            CommandHandler("start", add_account_cancel),
        ],
        per_message=False,
    )


def get_accounts_handlers() -> list:
    """Get all callback handlers for accounts (non-conversation)."""
    return [
        CommandHandler("accounts", cmd_accounts),
        CallbackQueryHandler(cb_accounts_list, pattern=f"^{CB_ACCOUNTS_LIST}$"),
        CallbackQueryHandler(cb_account_select, pattern=f"^{CB_ACCOUNT_SELECT}"),
        CallbackQueryHandler(cb_accounts_delete_list, pattern="^accounts_delete_list$"),
        CallbackQueryHandler(cb_account_delete, pattern=f"^{CB_ACCOUNT_DELETE}\\d+$"),
        CallbackQueryHandler(cb_account_delete_yes, pattern=f"^{CB_ACCOUNT_DELETE_YES}\\d+$"),
    ]
