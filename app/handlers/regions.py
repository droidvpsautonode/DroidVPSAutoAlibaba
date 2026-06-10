"""
Regions handler module.
Handles region scanning, caching, and selection.
"""

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from app.auth import owner_only
from app.db import db
from app.security import security
from app.keyboards import regions_keyboard, main_menu_keyboard
from app.states import CB_REGIONS_SCAN, CB_REGION_SELECT, CB_HOME
from app.utils import (
    show_loading, show_success, show_error,
    get_user_data, set_user_data, get_home_keyboard,
    CTX_CURRENT_ACCOUNT_ID, CTX_CURRENT_ACCOUNT_NAME, CTX_CURRENT_REGION,
)
from app.services.ecs_service import ECSService


def _get_ecs_service(context) -> tuple:
    """
    Get ECS service for current account.
    Returns (ecs_service, account_name) or (None, error_msg).
    """
    account_id = get_user_data(context, CTX_CURRENT_ACCOUNT_ID)
    if not account_id:
        return None, "Belum ada akun terpilih. Pilih akun terlebih dahulu."

    account = db.get_account_by_id(account_id)
    if not account:
        return None, "Akun tidak ditemukan di database."

    # Decrypt secret
    from app.security import security
    try:
        decrypted_secret = security.decrypt(account["access_key_secret_encrypted"])
    except Exception:
        return None, "Gagal mendekripsi AccessKey Secret. Periksa MASTER_KEY."

    ecs = ECSService(account["access_key_id"], decrypted_secret)
    return ecs, account["account_name"]


# ==================== SCAN REGIONS ====================

@owner_only
async def cb_regions_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Scan all regions for instances."""
    query = update.callback_query
    await query.answer()

    account_id = get_user_data(context, CTX_CURRENT_ACCOUNT_ID)
    if not account_id:
        await show_error(
            query,
            "Belum ada akun terpilih. Pilih akun terlebih dahulu.",
            main_menu_keyboard()
        )
        return

    await show_loading(query, "⏳ Scanning semua region...\nIni mungkin memerlukan waktu 30-60 detik.")

    ecs, account_name = _get_ecs_service(context)
    if ecs is None:
        await show_error(query, account_name)
        return

    try:
        active_regions = await ecs.scan_regions_with_instances()

        # Cache to database
        db.set_region_cache(account_id, active_regions)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="scan_regions",
            account_name=account_name,
            status="success"
        )

        if not active_regions:
            await query.edit_message_text(
                f"<b>🌏 Region Scan - {account_name}</b>\n\n"
                "Tidak ditemukan instance ECS di region manapun.\n"
                "Pastikan akun memiliki instance aktif.",
                reply_markup=main_menu_keyboard(),
                parse_mode="HTML"
            )
            return

        text = (
            f"<b>🌏 Region Aktif - {account_name}</b>\n\n"
            f"Ditemukan <b>{len(active_regions)}</b> region dengan instance:\n\n"
        )
        for r in active_regions:
            text += f"• {r['region_name']} (<code>{r['region_id']}</code>) - {r['instance_count']} instance\n"
        text += "\nPilih region:"

        await query.edit_message_text(
            text,
            reply_markup=regions_keyboard(active_regions),
            parse_mode="HTML"
        )

    except Exception as e:
        error_msg = ECSService._parse_error(e)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="scan_regions",
            account_name=account_name,
            status="failed",
            error_message=error_msg
        )
        await show_error(query, f"Scan region gagal: {error_msg}")


@owner_only
async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /scan command."""
    account_id = get_user_data(context, CTX_CURRENT_ACCOUNT_ID)
    if not account_id:
        await update.message.reply_text(
            "❌ Belum ada akun terpilih. Pilih akun terlebih dahulu.",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
        return

    loading_msg = await update.message.reply_text(
        "⏳ Scanning semua region...\nIni mungkin memerlukan waktu 30-60 detik.",
        parse_mode="HTML"
    )

    ecs, account_name = _get_ecs_service(context)
    if ecs is None:
        await loading_msg.edit_text(f"❌ {account_name}")
        return

    try:
        active_regions = await ecs.scan_regions_with_instances()

        # Cache to database
        db.set_region_cache(account_id, active_regions)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="scan_regions",
            account_name=account_name,
            status="success"
        )

        if not active_regions:
            await loading_msg.edit_text(
                f"<b>🌏 Region Scan - {account_name}</b>\n\n"
                "Tidak ditemukan instance ECS di region manapun.",
                reply_markup=main_menu_keyboard(),
                parse_mode="HTML"
            )
            return

        text = (
            f"<b>🌏 Region Aktif - {account_name}</b>\n\n"
            f"Ditemukan <b>{len(active_regions)}</b> region dengan instance:\n\n"
        )
        for r in active_regions:
            text += f"• {r['region_name']} (<code>{r['region_id']}</code>) - {r['instance_count']} instance\n"
        text += "\nPilih region:"

        await loading_msg.edit_text(
            text,
            reply_markup=regions_keyboard(active_regions),
            parse_mode="HTML"
        )

    except Exception as e:
        error_msg = ECSService._parse_error(e)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="scan_regions",
            account_name=account_name,
            status="failed",
            error_message=error_msg
        )
        await loading_msg.edit_text(
            f"❌ Scan region gagal: {error_msg}",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )


# ==================== CACHED REGIONS ====================

@owner_only
async def cb_regions_cached(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show cached regions without re-scanning."""
    query = update.callback_query
    await query.answer()

    account_id = get_user_data(context, CTX_CURRENT_ACCOUNT_ID)
    account_name = get_user_data(context, CTX_CURRENT_ACCOUNT_NAME, "Unknown")

    if not account_id:
        await show_error(
            query,
            "Belum ada akun terpilih.",
            main_menu_keyboard()
        )
        return

    cached_regions = db.get_region_cache(account_id)
    last_update = db.get_region_cache_updated_at(account_id)

    if not cached_regions:
        await query.edit_message_text(
            f"<b>🌏 Cache Region - {account_name}</b>\n\n"
            "Belum ada cache region. Gunakan <b>🔄 Scan Region</b> untuk memindai.",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
        return

    text = (
        f"<b>🌏 Cache Region - {account_name}</b>\n\n"
        f"Ditemukan <b>{len(cached_regions)}</b> region dengan instance:\n\n"
    )
    for r in cached_regions:
        text += f"• {r['region_name']} (<code>{r['region_id']}</code>) - {r['instance_count']} instance\n"

    if last_update:
        text += f"\n📅 <i>Terakhir update: {last_update}</i>\n"
    text += "\nPilih region:"

    await query.edit_message_text(
        text,
        reply_markup=regions_keyboard(cached_regions),
        parse_mode="HTML"
    )


# ==================== SELECT REGION ====================

@owner_only
async def cb_region_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle region selection - store and move to instances."""
    query = update.callback_query
    await query.answer()

    region_id = query.data.replace(CB_REGION_SELECT, "")
    set_user_data(context, CTX_CURRENT_REGION, region_id)

    account_id = get_user_data(context, CTX_CURRENT_ACCOUNT_ID)
    account_name = get_user_data(context, CTX_CURRENT_ACCOUNT_NAME, "Unknown")

    await show_loading(query, f"⏳ Memuat instance di region {region_id}...")

    ecs, err = _get_ecs_service(context)
    if ecs is None:
        await show_error(query, err)
        return

    try:
        instances = await ecs.describe_instances(region_id)

        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="list_instances",
            account_name=account_name,
            region_id=region_id,
            status="success"
        )

        if not instances:
            await query.edit_message_text(
                f"<b>📋 Instance - {region_id}</b>\n\n"
                "Tidak ada instance di region ini.",
                reply_markup=main_menu_keyboard(),
                parse_mode="HTML"
            )
            return

        # Store instances in context for detail view
        set_user_data(context, "cached_instances", instances)

        from app.keyboards import instances_keyboard
        from app.utils import format_status_emoji, format_instance_type_label

        text = (
            f"<b>📋 Instance - {account_name}</b>\n"
            f"<b>Region:</b> {region_id}\n"
            f"<b>Total:</b> {len(instances)} instance\n\n"
        )

        for inst in instances:
            status = format_status_emoji(inst["status"])
            os_label = format_instance_type_label(inst.get("os_type", ""))
            public_ip = ", ".join(inst.get("public_ips", [])) or "N/A"
            text += (
                f"• {os_label} <b>{inst['instance_name']}</b>\n"
                f"  {status} | IP: <code>{public_ip}</code>\n"
            )

        text += "\nPilih instance untuk detail & aksi:"

        await query.edit_message_text(
            text,
            reply_markup=instances_keyboard(instances),
            parse_mode="HTML"
        )

    except Exception as e:
        error_msg = ECSService._parse_error(e)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="list_instances",
            account_name=account_name,
            region_id=region_id,
            status="failed",
            error_message=error_msg
        )
        await show_error(query, f"Gagal memuat instance: {error_msg}")


# ==================== HANDLER REGISTRATION ====================

def get_regions_handlers() -> list:
    """Get all handlers for regions module."""
    return [
        CommandHandler("scan", cmd_scan),
        CallbackQueryHandler(cb_regions_scan, pattern=f"^{CB_REGIONS_SCAN}$"),
        CallbackQueryHandler(cb_regions_cached, pattern="^regions_cached$"),
        CallbackQueryHandler(cb_region_select, pattern=f"^{CB_REGION_SELECT}"),
    ]
