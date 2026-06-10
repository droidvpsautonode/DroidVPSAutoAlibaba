"""
Actions handler module.
Handles all instance actions: reboot, start, stop, delete,
reset password, reinstall OS, and security group management.
"""

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes, CallbackQueryHandler,
    ConversationHandler, MessageHandler, CommandHandler, filters,
)

from app.auth import owner_only
from app.db import db
from app.security import security
from app.keyboards import (
    confirm_action_keyboard, confirm_dangerous_keyboard,
    instance_detail_keyboard, main_menu_keyboard, cancel_keyboard,
)
from app.states import (
    CB_ACTION_REBOOT, CB_ACTION_START, CB_ACTION_STOP, CB_ACTION_DELETE,
    CB_ACTION_RESET_PWD, CB_ACTION_REINSTALL,
    CB_SG_OPEN_TCP, CB_SG_OPEN_UDP, CB_SG_OPEN_ALL,
    CB_SG_REVOKE_TCP, CB_SG_REVOKE_UDP, CB_SG_REVOKE_ALL,
    CB_CONFIRM_REBOOT, CB_CONFIRM_STOP, CB_CONFIRM_START,
    CB_CONFIRM_SG_TCP, CB_CONFIRM_SG_UDP, CB_CONFIRM_SG_ALL,
    CB_CONFIRM_REV_TCP, CB_CONFIRM_REV_UDP, CB_CONFIRM_REV_ALL,
    CB_HOME, CB_CANCEL,
    STATE_RESET_PASSWORD_INPUT, STATE_DELETE_INSTANCE_CONFIRM,
    STATE_REINSTALL_IMAGE_ID, STATE_REINSTALL_PASSWORD, STATE_REINSTALL_CONFIRM,
    STATE_OPEN_ALL_CONFIRM,
)
from app.utils import (
    show_loading, show_success, show_error, get_home_keyboard,
    get_user_data, set_user_data, validate_alibaba_password,
    CTX_CURRENT_ACCOUNT_ID, CTX_CURRENT_ACCOUNT_NAME,
    CTX_CURRENT_REGION, CTX_CURRENT_INSTANCE_ID,
    CTX_TEMP_PASSWORD, CTX_TEMP_IMAGE_ID,
)
from app.services.ecs_service import ECSService


def _get_ecs_service(context) -> tuple:
    """Get ECS service for current account."""
    account_id = get_user_data(context, CTX_CURRENT_ACCOUNT_ID)
    if not account_id:
        return None, "Belum ada akun terpilih."

    account = db.get_account_by_id(account_id)
    if not account:
        return None, "Akun tidak ditemukan."

    try:
        decrypted_secret = security.decrypt(account["access_key_secret_encrypted"])
    except Exception:
        return None, "Gagal mendekripsi AccessKey Secret."

    ecs = ECSService(account["access_key_id"], decrypted_secret)
    return ecs, account["account_name"]


def _get_instance_sg(context, instance_id: str) -> str:
    """Get first security group ID from cached instance."""
    cached = get_user_data(context, "cached_instances", [])
    for inst in cached:
        if inst["instance_id"] == instance_id:
            sg_ids = inst.get("security_group_ids", [])
            if sg_ids:
                return sg_ids[0]
    return ""


# ==================== REBOOT ====================

@owner_only
async def cb_action_reboot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm reboot."""
    query = update.callback_query
    await query.answer()
    instance_id = query.data.replace(CB_ACTION_REBOOT, "")

    await query.edit_message_text(
        f"<b>🔄 Konfirmasi Reboot</b>\n\n"
        f"Instance: <code>{instance_id}</code>\n\n"
        f"Apakah Anda yakin ingin me-reboot instance ini?",
        reply_markup=confirm_action_keyboard(
            f"{CB_CONFIRM_REBOOT}{instance_id}",
            f"inst_sel:{instance_id}"
        ),
        parse_mode="HTML"
    )


@owner_only
async def cb_confirm_reboot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute reboot."""
    query = update.callback_query
    await query.answer()
    instance_id = query.data.replace(CB_CONFIRM_REBOOT, "")
    region_id = get_user_data(context, CTX_CURRENT_REGION)
    account_name = get_user_data(context, CTX_CURRENT_ACCOUNT_NAME, "")

    await show_loading(query, "⏳ Memproses reboot instance...")

    ecs, err = _get_ecs_service(context)
    if ecs is None:
        await show_error(query, err)
        return

    try:
        result = await ecs.reboot_instance(region_id, instance_id)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="reboot_instance",
            account_name=account_name,
            region_id=region_id,
            instance_id=instance_id,
            status="success"
        )
        await show_success(query, result, instance_detail_keyboard(instance_id))
    except Exception as e:
        error_msg = ECSService._parse_error(e)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="reboot_instance",
            account_name=account_name,
            region_id=region_id,
            instance_id=instance_id,
            status="failed",
            error_message=error_msg
        )
        await show_error(query, error_msg, instance_detail_keyboard(instance_id))


# ==================== START ====================

@owner_only
async def cb_action_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm start."""
    query = update.callback_query
    await query.answer()
    instance_id = query.data.replace(CB_ACTION_START, "")

    await query.edit_message_text(
        f"<b>▶️ Konfirmasi Start</b>\n\n"
        f"Instance: <code>{instance_id}</code>\n\n"
        f"Apakah Anda yakin ingin menyalakan instance ini?",
        reply_markup=confirm_action_keyboard(
            f"{CB_CONFIRM_START}{instance_id}",
            f"inst_sel:{instance_id}"
        ),
        parse_mode="HTML"
    )


@owner_only
async def cb_confirm_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute start."""
    query = update.callback_query
    await query.answer()
    instance_id = query.data.replace(CB_CONFIRM_START, "")
    region_id = get_user_data(context, CTX_CURRENT_REGION)
    account_name = get_user_data(context, CTX_CURRENT_ACCOUNT_NAME, "")

    await show_loading(query, "⏳ Memproses start instance...")

    ecs, err = _get_ecs_service(context)
    if ecs is None:
        await show_error(query, err)
        return

    try:
        result = await ecs.start_instance(region_id, instance_id)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="start_instance",
            account_name=account_name,
            region_id=region_id,
            instance_id=instance_id,
            status="success"
        )
        await show_success(query, result, instance_detail_keyboard(instance_id))
    except Exception as e:
        error_msg = ECSService._parse_error(e)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="start_instance",
            account_name=account_name,
            region_id=region_id,
            instance_id=instance_id,
            status="failed",
            error_message=error_msg
        )
        await show_error(query, error_msg, instance_detail_keyboard(instance_id))


# ==================== STOP / SHUTDOWN ====================

@owner_only
async def cb_action_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm stop."""
    query = update.callback_query
    await query.answer()
    instance_id = query.data.replace(CB_ACTION_STOP, "")

    await query.edit_message_text(
        f"<b>⏹ Konfirmasi Shutdown</b>\n\n"
        f"Instance: <code>{instance_id}</code>\n\n"
        f"Apakah Anda yakin ingin mematikan instance ini?",
        reply_markup=confirm_action_keyboard(
            f"{CB_CONFIRM_STOP}{instance_id}",
            f"inst_sel:{instance_id}"
        ),
        parse_mode="HTML"
    )


@owner_only
async def cb_confirm_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute stop."""
    query = update.callback_query
    await query.answer()
    instance_id = query.data.replace(CB_CONFIRM_STOP, "")
    region_id = get_user_data(context, CTX_CURRENT_REGION)
    account_name = get_user_data(context, CTX_CURRENT_ACCOUNT_NAME, "")

    await show_loading(query, "⏳ Memproses shutdown instance...")

    ecs, err = _get_ecs_service(context)
    if ecs is None:
        await show_error(query, err)
        return

    try:
        result = await ecs.stop_instance(region_id, instance_id)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="stop_instance",
            account_name=account_name,
            region_id=region_id,
            instance_id=instance_id,
            status="success"
        )
        await show_success(query, result, instance_detail_keyboard(instance_id))
    except Exception as e:
        error_msg = ECSService._parse_error(e)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="stop_instance",
            account_name=account_name,
            region_id=region_id,
            instance_id=instance_id,
            status="failed",
            error_message=error_msg
        )
        await show_error(query, error_msg, instance_detail_keyboard(instance_id))


# ==================== SECURITY GROUP - OPEN TCP ====================

@owner_only
async def cb_sg_open_tcp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm open all TCP ports."""
    query = update.callback_query
    await query.answer()
    instance_id = query.data.replace(CB_SG_OPEN_TCP, "")

    await query.edit_message_text(
        f"<b>🌐 Open All TCP Ports</b>\n\n"
        f"Instance: <code>{instance_id}</code>\n\n"
        f"⚠️ <b>WARNING:</b> Ini akan membuka SEMUA port TCP (1-65535) "
        f"ke seluruh internet (0.0.0.0/0).\n\n"
        f"Lanjutkan hanya jika Anda memahami risikonya.",
        reply_markup=confirm_dangerous_keyboard(
            f"{CB_CONFIRM_SG_TCP}{instance_id}",
            f"inst_sel:{instance_id}"
        ),
        parse_mode="HTML"
    )


@owner_only
async def cb_confirm_sg_tcp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute open all TCP ports."""
    query = update.callback_query
    await query.answer()
    instance_id = query.data.replace(CB_CONFIRM_SG_TCP, "")
    region_id = get_user_data(context, CTX_CURRENT_REGION)
    account_name = get_user_data(context, CTX_CURRENT_ACCOUNT_NAME, "")

    sg_id = _get_instance_sg(context, instance_id)
    if not sg_id:
        await show_error(query, "Security group tidak ditemukan. Refresh detail instance.")
        return

    await show_loading(query, "⏳ Membuka semua port TCP...")

    ecs, err = _get_ecs_service(context)
    if ecs is None:
        await show_error(query, err)
        return

    try:
        result = await ecs.open_all_tcp(region_id, sg_id)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="open_all_tcp",
            account_name=account_name,
            region_id=region_id,
            instance_id=instance_id,
            status="success"
        )
        await show_success(query, result, instance_detail_keyboard(instance_id))
    except Exception as e:
        error_msg = ECSService._parse_error(e)
        if "already exists" in error_msg.lower() or "AuthorizationRuleExists" in str(e):
            await show_success(
                query,
                "Rule TCP 1/65535 sudah ada di security group.",
                instance_detail_keyboard(instance_id)
            )
        else:
            db.add_log(
                telegram_user_id=update.effective_user.id,
                action="open_all_tcp",
                account_name=account_name,
                region_id=region_id,
                instance_id=instance_id,
                status="failed",
                error_message=error_msg
            )
            await show_error(query, error_msg, instance_detail_keyboard(instance_id))


# ==================== SECURITY GROUP - OPEN UDP ====================

@owner_only
async def cb_sg_open_udp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm open all UDP ports."""
    query = update.callback_query
    await query.answer()
    instance_id = query.data.replace(CB_SG_OPEN_UDP, "")

    await query.edit_message_text(
        f"<b>🌐 Open All UDP Ports</b>\n\n"
        f"Instance: <code>{instance_id}</code>\n\n"
        f"⚠️ <b>WARNING:</b> Ini akan membuka SEMUA port UDP (1-65535) "
        f"ke seluruh internet (0.0.0.0/0).\n\n"
        f"Lanjutkan hanya jika Anda memahami risikonya.",
        reply_markup=confirm_dangerous_keyboard(
            f"{CB_CONFIRM_SG_UDP}{instance_id}",
            f"inst_sel:{instance_id}"
        ),
        parse_mode="HTML"
    )


@owner_only
async def cb_confirm_sg_udp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute open all UDP ports."""
    query = update.callback_query
    await query.answer()
    instance_id = query.data.replace(CB_CONFIRM_SG_UDP, "")
    region_id = get_user_data(context, CTX_CURRENT_REGION)
    account_name = get_user_data(context, CTX_CURRENT_ACCOUNT_NAME, "")

    sg_id = _get_instance_sg(context, instance_id)
    if not sg_id:
        await show_error(query, "Security group tidak ditemukan. Refresh detail instance.")
        return

    await show_loading(query, "⏳ Membuka semua port UDP...")

    ecs, err = _get_ecs_service(context)
    if ecs is None:
        await show_error(query, err)
        return

    try:
        result = await ecs.open_all_udp(region_id, sg_id)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="open_all_udp",
            account_name=account_name,
            region_id=region_id,
            instance_id=instance_id,
            status="success"
        )
        await show_success(query, result, instance_detail_keyboard(instance_id))
    except Exception as e:
        error_msg = ECSService._parse_error(e)
        if "already exists" in error_msg.lower() or "AuthorizationRuleExists" in str(e):
            await show_success(
                query,
                "Rule UDP 1/65535 sudah ada di security group.",
                instance_detail_keyboard(instance_id)
            )
        else:
            db.add_log(
                telegram_user_id=update.effective_user.id,
                action="open_all_udp",
                account_name=account_name,
                region_id=region_id,
                instance_id=instance_id,
                status="failed",
                error_message=error_msg
            )
            await show_error(query, error_msg, instance_detail_keyboard(instance_id))


# ==================== SECURITY GROUP - OPEN ALL TCP + UDP ====================

@owner_only
async def cb_sg_open_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm open all TCP + UDP ports (double confirmation step 1)."""
    query = update.callback_query
    await query.answer()
    instance_id = query.data.replace(CB_SG_OPEN_ALL, "")
    set_user_data(context, CTX_CURRENT_INSTANCE_ID, instance_id)

    await query.edit_message_text(
        f"<b>🌐 Open All TCP + UDP Ports</b>\n\n"
        f"Instance: <code>{instance_id}</code>\n\n"
        f"⚠️ <b>WARNING:</b> This will open ALL TCP and UDP ports "
        f"to the public internet: 0.0.0.0/0.\n"
        f"Only continue if you understand the risk.\n\n"
        f"⚠️ <b>PERINGATAN:</b> Ini akan membuka SEMUA port TCP DAN UDP "
        f"(1-65535) ke seluruh internet.\n\n"
        f"Tahap 1/2: Klik tombol di bawah jika Anda mengerti risikonya.",
        reply_markup=confirm_dangerous_keyboard(
            f"{CB_CONFIRM_SG_ALL}{instance_id}",
            f"inst_sel:{instance_id}"
        ),
        parse_mode="HTML"
    )


@owner_only
async def cb_confirm_sg_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Double confirmation step 2 - ask user to type confirmation text."""
    query = update.callback_query
    await query.answer()
    instance_id = query.data.replace(CB_CONFIRM_SG_ALL, "")
    set_user_data(context, CTX_CURRENT_INSTANCE_ID, instance_id)
    set_user_data(context, "awaiting_sg_all_confirm", True)

    await query.edit_message_text(
        f"<b>🌐 Open All TCP + UDP - Konfirmasi Final</b>\n\n"
        f"Instance: <code>{instance_id}</code>\n\n"
        f"Tahap 2/2: Ketik persis:\n"
        f"<code>CONFIRM OPEN ALL {instance_id}</code>\n\n"
        f"Ketik /cancel untuk membatalkan.",
        parse_mode="HTML"
    )
    return STATE_OPEN_ALL_CONFIRM


@owner_only
async def msg_confirm_sg_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process typed confirmation for open all TCP + UDP."""
    instance_id = get_user_data(context, CTX_CURRENT_INSTANCE_ID)
    expected = f"CONFIRM OPEN ALL {instance_id}"

    if update.message.text.strip() != expected:
        await update.message.reply_text(
            f"❌ Konfirmasi tidak cocok.\n\n"
            f"Ketik persis: <code>{expected}</code>\n"
            f"Atau ketik /cancel untuk membatalkan.",
            parse_mode="HTML"
        )
        return STATE_OPEN_ALL_CONFIRM

    region_id = get_user_data(context, CTX_CURRENT_REGION)
    account_name = get_user_data(context, CTX_CURRENT_ACCOUNT_NAME, "")

    sg_id = _get_instance_sg(context, instance_id)
    if not sg_id:
        await update.message.reply_text(
            "❌ Security group tidak ditemukan. Refresh detail instance.",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
        return ConversationHandler.END

    loading_msg = await update.message.reply_text(
        "⏳ Membuka semua port TCP + UDP...",
        parse_mode="HTML"
    )

    ecs, err = _get_ecs_service(context)
    if ecs is None:
        await loading_msg.edit_text(f"❌ {err}", parse_mode="HTML")
        return ConversationHandler.END

    try:
        result = await ecs.open_all_tcp_udp(region_id, sg_id)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="open_all_tcp_udp",
            account_name=account_name,
            region_id=region_id,
            instance_id=instance_id,
            status="success"
        )
        await loading_msg.edit_text(
            f"✅ <b>Berhasil!</b>\n\n{result}",
            reply_markup=instance_detail_keyboard(instance_id),
            parse_mode="HTML"
        )
    except Exception as e:
        error_msg = ECSService._parse_error(e)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="open_all_tcp_udp",
            account_name=account_name,
            region_id=region_id,
            instance_id=instance_id,
            status="failed",
            error_message=error_msg
        )
        await loading_msg.edit_text(
            f"❌ Gagal: {error_msg}",
            reply_markup=instance_detail_keyboard(instance_id),
            parse_mode="HTML"
        )

    set_user_data(context, "awaiting_sg_all_confirm", False)
    return ConversationHandler.END


# ==================== SECURITY GROUP - REVOKE TCP ====================

@owner_only
async def cb_sg_revoke_tcp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm revoke all TCP."""
    query = update.callback_query
    await query.answer()
    instance_id = query.data.replace(CB_SG_REVOKE_TCP, "")

    await query.edit_message_text(
        f"<b>🔒 Revoke All TCP Ports</b>\n\n"
        f"Instance: <code>{instance_id}</code>\n\n"
        f"Ini akan menghapus rule TCP 1/65535 dari 0.0.0.0/0.\n"
        f"Lanjutkan?",
        reply_markup=confirm_action_keyboard(
            f"{CB_CONFIRM_REV_TCP}{instance_id}",
            f"inst_sel:{instance_id}"
        ),
        parse_mode="HTML"
    )


@owner_only
async def cb_confirm_rev_tcp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute revoke all TCP."""
    query = update.callback_query
    await query.answer()
    instance_id = query.data.replace(CB_CONFIRM_REV_TCP, "")
    region_id = get_user_data(context, CTX_CURRENT_REGION)
    account_name = get_user_data(context, CTX_CURRENT_ACCOUNT_NAME, "")

    sg_id = _get_instance_sg(context, instance_id)
    if not sg_id:
        await show_error(query, "Security group tidak ditemukan.")
        return

    await show_loading(query, "⏳ Menutup semua port TCP...")

    ecs, err = _get_ecs_service(context)
    if ecs is None:
        await show_error(query, err)
        return

    try:
        result = await ecs.revoke_all_tcp(region_id, sg_id)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="revoke_all_tcp",
            account_name=account_name,
            region_id=region_id,
            instance_id=instance_id,
            status="success"
        )
        await show_success(query, result, instance_detail_keyboard(instance_id))
    except Exception as e:
        error_msg = ECSService._parse_error(e)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="revoke_all_tcp",
            account_name=account_name,
            region_id=region_id,
            instance_id=instance_id,
            status="failed",
            error_message=error_msg
        )
        await show_error(query, error_msg, instance_detail_keyboard(instance_id))


# ==================== SECURITY GROUP - REVOKE UDP ====================

@owner_only
async def cb_sg_revoke_udp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm revoke all UDP."""
    query = update.callback_query
    await query.answer()
    instance_id = query.data.replace(CB_SG_REVOKE_UDP, "")

    await query.edit_message_text(
        f"<b>🔒 Revoke All UDP Ports</b>\n\n"
        f"Instance: <code>{instance_id}</code>\n\n"
        f"Ini akan menghapus rule UDP 1/65535 dari 0.0.0.0/0.\n"
        f"Lanjutkan?",
        reply_markup=confirm_action_keyboard(
            f"{CB_CONFIRM_REV_UDP}{instance_id}",
            f"inst_sel:{instance_id}"
        ),
        parse_mode="HTML"
    )


@owner_only
async def cb_confirm_rev_udp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute revoke all UDP."""
    query = update.callback_query
    await query.answer()
    instance_id = query.data.replace(CB_CONFIRM_REV_UDP, "")
    region_id = get_user_data(context, CTX_CURRENT_REGION)
    account_name = get_user_data(context, CTX_CURRENT_ACCOUNT_NAME, "")

    sg_id = _get_instance_sg(context, instance_id)
    if not sg_id:
        await show_error(query, "Security group tidak ditemukan.")
        return

    await show_loading(query, "⏳ Menutup semua port UDP...")

    ecs, err = _get_ecs_service(context)
    if ecs is None:
        await show_error(query, err)
        return

    try:
        result = await ecs.revoke_all_udp(region_id, sg_id)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="revoke_all_udp",
            account_name=account_name,
            region_id=region_id,
            instance_id=instance_id,
            status="success"
        )
        await show_success(query, result, instance_detail_keyboard(instance_id))
    except Exception as e:
        error_msg = ECSService._parse_error(e)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="revoke_all_udp",
            account_name=account_name,
            region_id=region_id,
            instance_id=instance_id,
            status="failed",
            error_message=error_msg
        )
        await show_error(query, error_msg, instance_detail_keyboard(instance_id))


# ==================== SECURITY GROUP - REVOKE ALL TCP + UDP ====================

@owner_only
async def cb_sg_revoke_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm revoke all TCP + UDP."""
    query = update.callback_query
    await query.answer()
    instance_id = query.data.replace(CB_SG_REVOKE_ALL, "")

    await query.edit_message_text(
        f"<b>🔒 Revoke All TCP + UDP Ports</b>\n\n"
        f"Instance: <code>{instance_id}</code>\n\n"
        f"Ini akan menghapus rule TCP dan UDP 1/65535 dari 0.0.0.0/0.\n"
        f"Lanjutkan?",
        reply_markup=confirm_action_keyboard(
            f"{CB_CONFIRM_REV_ALL}{instance_id}",
            f"inst_sel:{instance_id}"
        ),
        parse_mode="HTML"
    )


@owner_only
async def cb_confirm_rev_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute revoke all TCP + UDP."""
    query = update.callback_query
    await query.answer()
    instance_id = query.data.replace(CB_CONFIRM_REV_ALL, "")
    region_id = get_user_data(context, CTX_CURRENT_REGION)
    account_name = get_user_data(context, CTX_CURRENT_ACCOUNT_NAME, "")

    sg_id = _get_instance_sg(context, instance_id)
    if not sg_id:
        await show_error(query, "Security group tidak ditemukan.")
        return

    await show_loading(query, "⏳ Menutup semua port TCP + UDP...")

    ecs, err = _get_ecs_service(context)
    if ecs is None:
        await show_error(query, err)
        return

    try:
        result = await ecs.revoke_all_tcp_udp(region_id, sg_id)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="revoke_all_tcp_udp",
            account_name=account_name,
            region_id=region_id,
            instance_id=instance_id,
            status="success"
        )
        await show_success(query, result, instance_detail_keyboard(instance_id))
    except Exception as e:
        error_msg = ECSService._parse_error(e)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="revoke_all_tcp_udp",
            account_name=account_name,
            region_id=region_id,
            instance_id=instance_id,
            status="failed",
            error_message=error_msg
        )
        await show_error(query, error_msg, instance_detail_keyboard(instance_id))


# ==================== RESET PASSWORD ====================

@owner_only
async def cb_action_reset_pwd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start reset password flow."""
    query = update.callback_query
    await query.answer()
    instance_id = query.data.replace(CB_ACTION_RESET_PWD, "")
    set_user_data(context, CTX_CURRENT_INSTANCE_ID, instance_id)

    await query.edit_message_text(
        f"<b>🔐 Reset Password</b>\n\n"
        f"Instance: <code>{instance_id}</code>\n\n"
        f"Masukkan password baru.\n\n"
        f"<b>Aturan password Alibaba ECS:</b>\n"
        f"• 8-30 karakter\n"
        f"• Minimal 3 dari: huruf besar, huruf kecil, angka, karakter spesial\n\n"
        f"Ketik /cancel untuk membatalkan.",
        parse_mode="HTML"
    )
    return STATE_RESET_PASSWORD_INPUT


@owner_only
async def msg_reset_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and validate new password, then execute."""
    password = update.message.text.strip()

    # Try to delete message with password
    try:
        await update.message.delete()
    except Exception:
        pass

    # Validate password
    is_valid, error_msg = validate_alibaba_password(password)
    if not is_valid:
        await update.effective_chat.send_message(
            f"❌ {error_msg}\n\nCoba lagi atau ketik /cancel:",
            parse_mode="HTML"
        )
        return STATE_RESET_PASSWORD_INPUT

    instance_id = get_user_data(context, CTX_CURRENT_INSTANCE_ID)
    region_id = get_user_data(context, CTX_CURRENT_REGION)
    account_name = get_user_data(context, CTX_CURRENT_ACCOUNT_NAME, "")

    loading_msg = await update.effective_chat.send_message(
        "⏳ Memproses reset password...",
        parse_mode="HTML"
    )

    ecs, err = _get_ecs_service(context)
    if ecs is None:
        await loading_msg.edit_text(f"❌ {err}", parse_mode="HTML")
        return ConversationHandler.END

    try:
        result = await ecs.reset_password(region_id, instance_id, password)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="reset_password",
            account_name=account_name,
            region_id=region_id,
            instance_id=instance_id,
            status="success"
        )
        await loading_msg.edit_text(
            f"✅ {result}",
            reply_markup=instance_detail_keyboard(instance_id),
            parse_mode="HTML"
        )
    except Exception as e:
        error_msg = ECSService._parse_error(e)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="reset_password",
            account_name=account_name,
            region_id=region_id,
            instance_id=instance_id,
            status="failed",
            error_message=error_msg
        )
        await loading_msg.edit_text(
            f"❌ Reset password gagal: {error_msg}",
            reply_markup=instance_detail_keyboard(instance_id),
            parse_mode="HTML"
        )

    return ConversationHandler.END


# ==================== DELETE INSTANCE ====================

@owner_only
async def cb_action_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start delete instance flow with double confirmation."""
    query = update.callback_query
    await query.answer()
    instance_id = query.data.replace(CB_ACTION_DELETE, "")
    set_user_data(context, CTX_CURRENT_INSTANCE_ID, instance_id)

    await query.edit_message_text(
        f"<b>🗑 Delete Instance</b>\n\n"
        f"Instance: <code>{instance_id}</code>\n\n"
        f"⚠️ <b>PERINGATAN KERAS:</b>\n"
        f"Menghapus instance bersifat <b>PERMANEN</b>.\n"
        f"Semua data akan hilang dan tidak bisa dikembalikan.\n\n"
        f"Untuk konfirmasi, ketik persis:\n"
        f"<code>CONFIRM DELETE {instance_id}</code>\n\n"
        f"Ketik /cancel untuk membatalkan.",
        parse_mode="HTML"
    )
    return STATE_DELETE_INSTANCE_CONFIRM


@owner_only
async def msg_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process typed confirmation for delete instance."""
    instance_id = get_user_data(context, CTX_CURRENT_INSTANCE_ID)
    expected = f"CONFIRM DELETE {instance_id}"

    if update.message.text.strip() != expected:
        await update.message.reply_text(
            f"❌ Konfirmasi tidak cocok.\n\n"
            f"Ketik persis: <code>{expected}</code>\n"
            f"Atau ketik /cancel untuk membatalkan.",
            parse_mode="HTML"
        )
        return STATE_DELETE_INSTANCE_CONFIRM

    region_id = get_user_data(context, CTX_CURRENT_REGION)
    account_name = get_user_data(context, CTX_CURRENT_ACCOUNT_NAME, "")

    loading_msg = await update.message.reply_text(
        "⏳ Menghapus instance...",
        parse_mode="HTML"
    )

    ecs, err = _get_ecs_service(context)
    if ecs is None:
        await loading_msg.edit_text(f"❌ {err}", parse_mode="HTML")
        return ConversationHandler.END

    try:
        result = await ecs.delete_instance(region_id, instance_id)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="delete_instance",
            account_name=account_name,
            region_id=region_id,
            instance_id=instance_id,
            status="success"
        )
        await loading_msg.edit_text(
            f"✅ {result}",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        error_msg = ECSService._parse_error(e)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="delete_instance",
            account_name=account_name,
            region_id=region_id,
            instance_id=instance_id,
            status="failed",
            error_message=error_msg
        )
        await loading_msg.edit_text(
            f"❌ Gagal menghapus instance: {error_msg}",
            reply_markup=instance_detail_keyboard(instance_id),
            parse_mode="HTML"
        )

    return ConversationHandler.END


# ==================== REINSTALL OS ====================

@owner_only
async def cb_action_reinstall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start reinstall OS flow."""
    query = update.callback_query
    await query.answer()
    instance_id = query.data.replace(CB_ACTION_REINSTALL, "")
    set_user_data(context, CTX_CURRENT_INSTANCE_ID, instance_id)

    await query.edit_message_text(
        f"<b>💿 Reinstall OS / Ganti System Disk</b>\n\n"
        f"Instance: <code>{instance_id}</code>\n\n"
        f"⚠️ <b>PERINGATAN:</b>\n"
        f"• Aksi ini akan MENGHAPUS semua data di system disk\n"
        f"• Instance harus dalam status <b>Stopped</b>\n"
        f"• Data disk tidak terpengaruh (jika ada)\n\n"
        f"Langkah 1/3: Masukkan <b>Image ID</b> untuk OS baru.\n"
        f"Contoh: <code>ubuntu_22_04_x64_20G_alibase_20230907.vhd</code>\n\n"
        f"Ketik /cancel untuk membatalkan.",
        parse_mode="HTML"
    )
    return STATE_REINSTALL_IMAGE_ID


@owner_only
async def msg_reinstall_image_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive image ID for reinstall."""
    image_id = update.message.text.strip()

    if len(image_id) < 5:
        await update.message.reply_text(
            "❌ Image ID terlalu pendek. Coba lagi:",
            parse_mode="HTML"
        )
        return STATE_REINSTALL_IMAGE_ID

    set_user_data(context, CTX_TEMP_IMAGE_ID, image_id)

    await update.message.reply_text(
        f"✅ Image ID: <code>{image_id}</code>\n\n"
        f"Langkah 2/3: Masukkan <b>password baru</b> untuk instance.\n\n"
        f"<b>Aturan password:</b>\n"
        f"• 8-30 karakter\n"
        f"• Minimal 3 dari: huruf besar, huruf kecil, angka, karakter spesial\n\n"
        f"Ketik /cancel untuk membatalkan.",
        parse_mode="HTML"
    )
    return STATE_REINSTALL_PASSWORD


@owner_only
async def msg_reinstall_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive password for reinstall."""
    password = update.message.text.strip()

    # Delete message with password
    try:
        await update.message.delete()
    except Exception:
        pass

    # Validate
    is_valid, error_msg = validate_alibaba_password(password)
    if not is_valid:
        await update.effective_chat.send_message(
            f"❌ {error_msg}\n\nCoba lagi atau ketik /cancel:",
            parse_mode="HTML"
        )
        return STATE_REINSTALL_PASSWORD

    set_user_data(context, CTX_TEMP_PASSWORD, password)
    instance_id = get_user_data(context, CTX_CURRENT_INSTANCE_ID)
    image_id = get_user_data(context, CTX_TEMP_IMAGE_ID)

    await update.effective_chat.send_message(
        f"<b>💿 Konfirmasi Reinstall OS</b>\n\n"
        f"Instance: <code>{instance_id}</code>\n"
        f"Image: <code>{image_id}</code>\n\n"
        f"⚠️ <b>PERINGATAN KERAS:</b>\n"
        f"Semua data di system disk akan DIHAPUS PERMANEN!\n\n"
        f"Langkah 3/3: Ketik persis untuk konfirmasi:\n"
        f"<code>CONFIRM REINSTALL {instance_id}</code>\n\n"
        f"Ketik /cancel untuk membatalkan.",
        parse_mode="HTML"
    )
    return STATE_REINSTALL_CONFIRM


@owner_only
async def msg_reinstall_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process typed confirmation for reinstall."""
    instance_id = get_user_data(context, CTX_CURRENT_INSTANCE_ID)
    expected = f"CONFIRM REINSTALL {instance_id}"

    if update.message.text.strip() != expected:
        await update.message.reply_text(
            f"❌ Konfirmasi tidak cocok.\n\n"
            f"Ketik persis: <code>{expected}</code>\n"
            f"Atau ketik /cancel untuk membatalkan.",
            parse_mode="HTML"
        )
        return STATE_REINSTALL_CONFIRM

    region_id = get_user_data(context, CTX_CURRENT_REGION)
    account_name = get_user_data(context, CTX_CURRENT_ACCOUNT_NAME, "")
    image_id = get_user_data(context, CTX_TEMP_IMAGE_ID)
    password = get_user_data(context, CTX_TEMP_PASSWORD)

    loading_msg = await update.message.reply_text(
        "⏳ Memproses reinstall OS...",
        parse_mode="HTML"
    )

    ecs, err = _get_ecs_service(context)
    if ecs is None:
        await loading_msg.edit_text(f"❌ {err}", parse_mode="HTML")
        context.user_data.pop(CTX_TEMP_PASSWORD, None)
        context.user_data.pop(CTX_TEMP_IMAGE_ID, None)
        return ConversationHandler.END

    try:
        result = await ecs.replace_system_disk(region_id, instance_id, image_id, password)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="reinstall_os",
            account_name=account_name,
            region_id=region_id,
            instance_id=instance_id,
            status="success"
        )
        await loading_msg.edit_text(
            f"✅ {result}",
            reply_markup=instance_detail_keyboard(instance_id),
            parse_mode="HTML"
        )
    except Exception as e:
        error_msg = ECSService._parse_error(e)
        db.add_log(
            telegram_user_id=update.effective_user.id,
            action="reinstall_os",
            account_name=account_name,
            region_id=region_id,
            instance_id=instance_id,
            status="failed",
            error_message=error_msg
        )
        await loading_msg.edit_text(
            f"❌ Reinstall gagal: {error_msg}",
            reply_markup=instance_detail_keyboard(instance_id),
            parse_mode="HTML"
        )

    # Clear temp data
    context.user_data.pop(CTX_TEMP_PASSWORD, None)
    context.user_data.pop(CTX_TEMP_IMAGE_ID, None)
    return ConversationHandler.END


# ==================== CANCEL HANDLER ====================

async def action_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel any action conversation."""
    context.user_data.pop(CTX_TEMP_PASSWORD, None)
    context.user_data.pop(CTX_TEMP_IMAGE_ID, None)
    context.user_data.pop("awaiting_sg_all_confirm", None)

    await update.message.reply_text(
        "❌ Operasi dibatalkan.",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )
    return ConversationHandler.END


# ==================== CONVERSATION HANDLERS ====================

def get_reset_password_conversation() -> ConversationHandler:
    """Get ConversationHandler for reset password."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cb_action_reset_pwd, pattern=f"^{CB_ACTION_RESET_PWD}"),
        ],
        states={
            STATE_RESET_PASSWORD_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_reset_password),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", action_cancel),
            CommandHandler("start", action_cancel),
        ],
        per_message=False,
    )


def get_delete_instance_conversation() -> ConversationHandler:
    """Get ConversationHandler for delete instance."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cb_action_delete, pattern=f"^{CB_ACTION_DELETE}"),
        ],
        states={
            STATE_DELETE_INSTANCE_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_delete_confirm),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", action_cancel),
            CommandHandler("start", action_cancel),
        ],
        per_message=False,
    )


def get_reinstall_conversation() -> ConversationHandler:
    """Get ConversationHandler for reinstall OS."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cb_action_reinstall, pattern=f"^{CB_ACTION_REINSTALL}"),
        ],
        states={
            STATE_REINSTALL_IMAGE_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_reinstall_image_id),
            ],
            STATE_REINSTALL_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_reinstall_password),
            ],
            STATE_REINSTALL_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_reinstall_confirm),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", action_cancel),
            CommandHandler("start", action_cancel),
        ],
        per_message=False,
    )


def get_open_all_conversation() -> ConversationHandler:
    """Get ConversationHandler for open all TCP + UDP (double confirm)."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cb_confirm_sg_all, pattern=f"^{CB_CONFIRM_SG_ALL}"),
        ],
        states={
            STATE_OPEN_ALL_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_confirm_sg_all),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", action_cancel),
            CommandHandler("start", action_cancel),
        ],
        per_message=False,
    )


# ==================== HANDLER REGISTRATION ====================

def get_actions_handlers() -> list:
    """Get all non-conversation callback handlers for actions."""
    return [
        # Reboot
        CallbackQueryHandler(cb_action_reboot, pattern=f"^{CB_ACTION_REBOOT}"),
        CallbackQueryHandler(cb_confirm_reboot, pattern=f"^{CB_CONFIRM_REBOOT}"),
        # Start
        CallbackQueryHandler(cb_action_start, pattern=f"^{CB_ACTION_START}"),
        CallbackQueryHandler(cb_confirm_start, pattern=f"^{CB_CONFIRM_START}"),
        # Stop
        CallbackQueryHandler(cb_action_stop, pattern=f"^{CB_ACTION_STOP}"),
        CallbackQueryHandler(cb_confirm_stop, pattern=f"^{CB_CONFIRM_STOP}"),
        # Security Group - Open
        CallbackQueryHandler(cb_sg_open_tcp, pattern=f"^{CB_SG_OPEN_TCP}"),
        CallbackQueryHandler(cb_confirm_sg_tcp, pattern=f"^{CB_CONFIRM_SG_TCP}"),
        CallbackQueryHandler(cb_sg_open_udp, pattern=f"^{CB_SG_OPEN_UDP}"),
        CallbackQueryHandler(cb_confirm_sg_udp, pattern=f"^{CB_CONFIRM_SG_UDP}"),
        CallbackQueryHandler(cb_sg_open_all, pattern=f"^{CB_SG_OPEN_ALL}"),
        # Security Group - Revoke
        CallbackQueryHandler(cb_sg_revoke_tcp, pattern=f"^{CB_SG_REVOKE_TCP}"),
        CallbackQueryHandler(cb_confirm_rev_tcp, pattern=f"^{CB_CONFIRM_REV_TCP}"),
        CallbackQueryHandler(cb_sg_revoke_udp, pattern=f"^{CB_SG_REVOKE_UDP}"),
        CallbackQueryHandler(cb_confirm_rev_udp, pattern=f"^{CB_CONFIRM_REV_UDP}"),
        CallbackQueryHandler(cb_sg_revoke_all, pattern=f"^{CB_SG_REVOKE_ALL}"),
        CallbackQueryHandler(cb_confirm_rev_all, pattern=f"^{CB_CONFIRM_REV_ALL}"),
    ]
