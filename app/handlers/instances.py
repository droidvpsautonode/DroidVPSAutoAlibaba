"""
Instances handler module.
Handles listing instances and showing instance details.
"""

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from app.auth import owner_only
from app.db import db
from app.security import security
from app.keyboards import (
    instances_keyboard, instance_detail_keyboard,
    main_menu_keyboard, back_home_keyboard,
)
from app.states import (
    CB_INSTANCES_LIST, CB_INSTANCE_SELECT, CB_INSTANCE_REFRESH,
    CB_BACK, CB_HOME,
)
from app.utils import (
    show_loading, show_error,
    get_user_data, set_user_data,
    format_status_emoji, format_instance_type_label,
    CTX_CURRENT_ACCOUNT_ID, CTX_CURRENT_ACCOUNT_NAME,
    CTX_CURRENT_REGION, CTX_CURRENT_INSTANCE_ID,
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

    try:
        decrypted_secret = security.decrypt(account["access_key_secret_encrypted"])
    except Exception:
        return None, "Gagal mendekripsi AccessKey Secret. Periksa MASTER_KEY."

    ecs = ECSService(account["access_key_id"], decrypted_secret)
    return ecs, account["account_name"]


# ==================== LIST INSTANCES ====================

@owner_only
async def cb_instances_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of instances in current region."""
    query = update.callback_query
    await query.answer()

    region_id = get_user_data(context, CTX_CURRENT_REGION)
    account_name = get_user_data(context, CTX_CURRENT_ACCOUNT_NAME, "Unknown")

    if not region_id:
        await show_error(
            query,
            "Belum ada region terpilih. Scan region terlebih dahulu.",
            main_menu_keyboard()
        )
        return

    await show_loading(query, f"⏳ Memuat instance di region {region_id}...")

    ecs, err = _get_ecs_service(context)
    if ecs is None:
        await show_error(query, err)
        return

    try:
        instances = await ecs.describe_instances(region_id)

        if not instances:
            await query.edit_message_text(
                f"<b>📋 Instance - {account_name}</b>\n"
                f"<b>Region:</b> {region_id}\n\n"
                "Tidak ada instance di region ini.",
                reply_markup=main_menu_keyboard(),
                parse_mode="HTML"
            )
            return

        # Cache instances in context
        set_user_data(context, "cached_instances", instances)

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
        await show_error(query, f"Gagal memuat instance: {error_msg}")


@owner_only
async def cmd_instances(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /instances command."""
    region_id = get_user_data(context, CTX_CURRENT_REGION)
    account_name = get_user_data(context, CTX_CURRENT_ACCOUNT_NAME, "Unknown")

    if not region_id:
        await update.message.reply_text(
            "❌ Belum ada region terpilih. Pilih akun dan scan region terlebih dahulu.",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
        return

    loading_msg = await update.message.reply_text(
        f"⏳ Memuat instance di region {region_id}...",
        parse_mode="HTML"
    )

    ecs, err = _get_ecs_service(context)
    if ecs is None:
        await loading_msg.edit_text(f"❌ {err}", parse_mode="HTML")
        return

    try:
        instances = await ecs.describe_instances(region_id)

        if not instances:
            await loading_msg.edit_text(
                f"<b>📋 Instance - {account_name}</b>\n"
                f"<b>Region:</b> {region_id}\n\n"
                "Tidak ada instance di region ini.",
                reply_markup=main_menu_keyboard(),
                parse_mode="HTML"
            )
            return

        set_user_data(context, "cached_instances", instances)

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

        await loading_msg.edit_text(
            text,
            reply_markup=instances_keyboard(instances),
            parse_mode="HTML"
        )

    except Exception as e:
        error_msg = ECSService._parse_error(e)
        await loading_msg.edit_text(
            f"❌ Gagal memuat instance: {error_msg}",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )


# ==================== INSTANCE DETAIL ====================

@owner_only
async def cb_instance_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show instance detail."""
    query = update.callback_query
    await query.answer()

    instance_id = query.data.replace(CB_INSTANCE_SELECT, "")
    set_user_data(context, CTX_CURRENT_INSTANCE_ID, instance_id)

    await _show_instance_detail(query, context, instance_id)


@owner_only
async def cb_instance_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Refresh instance detail."""
    query = update.callback_query
    await query.answer()

    instance_id = query.data.replace(CB_INSTANCE_REFRESH, "")
    set_user_data(context, CTX_CURRENT_INSTANCE_ID, instance_id)

    await show_loading(query, "⏳ Memuat ulang detail instance...")
    await _show_instance_detail(query, context, instance_id, refresh=True)


async def _show_instance_detail(query, context, instance_id: str, refresh: bool = False):
    """Internal: show instance detail card."""
    region_id = get_user_data(context, CTX_CURRENT_REGION)
    account_name = get_user_data(context, CTX_CURRENT_ACCOUNT_NAME, "Unknown")

    if not region_id:
        await show_error(query, "Region tidak ditemukan. Kembali ke menu utama.")
        return

    # Try to get from cache first
    instance = None
    if not refresh:
        cached = get_user_data(context, "cached_instances", [])
        for inst in cached:
            if inst["instance_id"] == instance_id:
                instance = inst
                break

    # If not in cache or refreshing, fetch from API
    if instance is None:
        ecs, err = _get_ecs_service(context)
        if ecs is None:
            await show_error(query, err)
            return

        try:
            instance = await ecs.describe_instance(region_id, instance_id)
        except Exception as e:
            error_msg = ECSService._parse_error(e)
            await show_error(query, f"Gagal memuat instance: {error_msg}")
            return

    if not instance:
        await show_error(query, "Instance tidak ditemukan.")
        return

    # Format detail card
    status = format_status_emoji(instance["status"])
    os_label = format_instance_type_label(instance.get("os_type", ""))
    public_ip = ", ".join(instance.get("public_ips", [])) or "N/A"
    private_ip = ", ".join(instance.get("private_ips", [])) or "N/A"
    sg_ids = ", ".join(instance.get("security_group_ids", [])) or "N/A"
    memory_gb = round(instance.get("memory", 0) / 1024, 1) if instance.get("memory") else "N/A"
    cpu = instance.get("cpu", "N/A")

    text = (
        f"<b>🖥 Detail Instance</b>\n"
        f"{'━' * 28}\n\n"
        f"📌 <b>Account:</b> {account_name}\n"
        f"🌏 <b>Region:</b> {region_id}\n"
        f"🔖 <b>Instance ID:</b>\n<code>{instance['instance_id']}</code>\n"
        f"📝 <b>Nama:</b> {instance['instance_name']}\n"
        f"📊 <b>Status:</b> {status}\n"
        f"💻 <b>Tipe:</b> {os_label}\n"
        f"🖼 <b>OS:</b> {instance.get('os_name', 'N/A')}\n"
        f"⚙️ <b>Spesifikasi:</b> {cpu} vCPU / {memory_gb} GB RAM\n"
        f"🔧 <b>Instance Type:</b> {instance.get('instance_type', 'N/A')}\n"
        f"🌐 <b>Public IP:</b> <code>{public_ip}</code>\n"
        f"🔒 <b>Private IP:</b> <code>{private_ip}</code>\n"
        f"🛡 <b>Security Group:</b>\n<code>{sg_ids}</code>\n"
    )

    if instance.get("expired_time"):
        text += f"📅 <b>Expired:</b> {instance['expired_time']}\n"
    if instance.get("image_id"):
        text += f"💿 <b>Image ID:</b>\n<code>{instance['image_id']}</code>\n"

    text += f"\n{'━' * 28}\nPilih aksi:"

    await query.edit_message_text(
        text,
        reply_markup=instance_detail_keyboard(instance_id),
        parse_mode="HTML"
    )


# ==================== BACK NAVIGATION ====================

@owner_only
async def cb_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back button - go back to instances list or regions."""
    query = update.callback_query
    await query.answer()

    region_id = get_user_data(context, CTX_CURRENT_REGION)
    if region_id:
        # Go back to instances list
        cached = get_user_data(context, "cached_instances", [])
        account_name = get_user_data(context, CTX_CURRENT_ACCOUNT_NAME, "Unknown")

        if cached:
            text = (
                f"<b>📋 Instance - {account_name}</b>\n"
                f"<b>Region:</b> {region_id}\n"
                f"<b>Total:</b> {len(cached)} instance\n\n"
            )
            for inst in cached:
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
                reply_markup=instances_keyboard(cached),
                parse_mode="HTML"
            )
            return

    # Fallback: go to main menu
    from app.handlers.start import WELCOME_TEXT
    await query.edit_message_text(
        WELCOME_TEXT,
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )


# ==================== HANDLER REGISTRATION ====================

def get_instances_handlers() -> list:
    """Get all handlers for instances module."""
    return [
        CommandHandler("instances", cmd_instances),
        CallbackQueryHandler(cb_instances_list, pattern=f"^{CB_INSTANCES_LIST}$"),
        CallbackQueryHandler(cb_instance_select, pattern=f"^{CB_INSTANCE_SELECT}"),
        CallbackQueryHandler(cb_instance_refresh, pattern=f"^{CB_INSTANCE_REFRESH}"),
        CallbackQueryHandler(cb_back, pattern=f"^{CB_BACK}$"),
    ]
