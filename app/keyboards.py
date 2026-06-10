"""
Keyboards module.
Centralized inline keyboard builders for the bot.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.states import (
    CB_MAIN_MENU, CB_ACCOUNTS_LIST, CB_ACCOUNT_SELECT, CB_ACCOUNT_DELETE,
    CB_ACCOUNT_DELETE_YES, CB_ACCOUNT_ADD, CB_REGIONS_SCAN, CB_REGION_SELECT,
    CB_INSTANCES_LIST, CB_INSTANCE_SELECT, CB_INSTANCE_REFRESH,
    CB_ACTION_REBOOT, CB_ACTION_START, CB_ACTION_STOP, CB_ACTION_DELETE,
    CB_ACTION_RESET_PWD, CB_ACTION_REINSTALL,
    CB_SG_OPEN_TCP, CB_SG_OPEN_UDP, CB_SG_OPEN_ALL,
    CB_SG_REVOKE_TCP, CB_SG_REVOKE_UDP, CB_SG_REVOKE_ALL,
    CB_CONFIRM_REBOOT, CB_CONFIRM_STOP, CB_CONFIRM_START,
    CB_CONFIRM_SG_TCP, CB_CONFIRM_SG_UDP, CB_CONFIRM_SG_ALL,
    CB_CONFIRM_REV_TCP, CB_CONFIRM_REV_UDP, CB_CONFIRM_REV_ALL,
    CB_HOME, CB_BACK, CB_LOGS, CB_HELP, CB_CANCEL, CB_NOOP,
)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu keyboard."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧭 Pilih Akun Alibaba", callback_data=CB_ACCOUNTS_LIST)],
        [InlineKeyboardButton("➕ Tambah Akun", callback_data=CB_ACCOUNT_ADD)],
        [InlineKeyboardButton("🗑 Hapus Akun", callback_data="accounts_delete_list")],
        [InlineKeyboardButton("🔄 Scan Region", callback_data=CB_REGIONS_SCAN)],
        [InlineKeyboardButton("📜 Logs", callback_data=CB_LOGS)],
        [InlineKeyboardButton("❓ Help", callback_data=CB_HELP)],
    ])


def accounts_list_keyboard(accounts: list[dict]) -> InlineKeyboardMarkup:
    """Keyboard with list of accounts to select."""
    buttons = []
    for acc in accounts:
        label = f"🔑 {acc['account_name']}"
        buttons.append([
            InlineKeyboardButton(
                label,
                callback_data=f"{CB_ACCOUNT_SELECT}{acc['id']}"
            )
        ])
    buttons.append([InlineKeyboardButton("🏠 Home", callback_data=CB_HOME)])
    return InlineKeyboardMarkup(buttons)


def accounts_delete_keyboard(accounts: list[dict]) -> InlineKeyboardMarkup:
    """Keyboard with list of accounts to delete."""
    buttons = []
    for acc in accounts:
        label = f"🗑 {acc['account_name']}"
        buttons.append([
            InlineKeyboardButton(
                label,
                callback_data=f"{CB_ACCOUNT_DELETE}{acc['id']}"
            )
        ])
    buttons.append([InlineKeyboardButton("🏠 Home", callback_data=CB_HOME)])
    return InlineKeyboardMarkup(buttons)


def account_delete_confirm_keyboard(account_id: int) -> InlineKeyboardMarkup:
    """Confirm delete account keyboard."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "⚠️ Ya, Hapus Akun Ini",
            callback_data=f"{CB_ACCOUNT_DELETE_YES}{account_id}"
        )],
        [InlineKeyboardButton("❌ Batal", callback_data=CB_HOME)],
    ])


def regions_keyboard(regions: list[dict]) -> InlineKeyboardMarkup:
    """Keyboard with list of regions."""
    buttons = []
    for region in regions:
        label = f"🌏 {region['region_name']} - {region['region_id']} ({region['instance_count']})"
        buttons.append([
            InlineKeyboardButton(
                label,
                callback_data=f"{CB_REGION_SELECT}{region['region_id']}"
            )
        ])
    buttons.append([
        InlineKeyboardButton("🔄 Refresh", callback_data=CB_REGIONS_SCAN),
    ])
    buttons.append([InlineKeyboardButton("🏠 Home", callback_data=CB_HOME)])
    return InlineKeyboardMarkup(buttons)


def instances_keyboard(instances: list[dict]) -> InlineKeyboardMarkup:
    """Keyboard with list of instances."""
    buttons = []
    for inst in instances:
        # Determine label
        status_icon = "🟢" if inst.get("status") == "Running" else (
            "🔴" if inst.get("status") == "Stopped" else "🟡"
        )
        os_label = "RDP" if inst.get("os_type", "").lower() == "windows" else "VPS"
        name = inst.get("instance_name", inst.get("instance_id", "Unknown"))
        label = f"{status_icon} [{os_label}] {name}"

        buttons.append([
            InlineKeyboardButton(
                label,
                callback_data=f"{CB_INSTANCE_SELECT}{inst['instance_id']}"
            )
        ])
    buttons.append([
        InlineKeyboardButton("🔙 Kembali", callback_data=CB_BACK),
        InlineKeyboardButton("🏠 Home", callback_data=CB_HOME),
    ])
    return InlineKeyboardMarkup(buttons)


def instance_detail_keyboard(instance_id: str) -> InlineKeyboardMarkup:
    """Keyboard with instance actions."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Reboot", callback_data=f"{CB_ACTION_REBOOT}{instance_id}"),
            InlineKeyboardButton("▶️ Start", callback_data=f"{CB_ACTION_START}{instance_id}"),
        ],
        [
            InlineKeyboardButton("⏹ Shutdown", callback_data=f"{CB_ACTION_STOP}{instance_id}"),
            InlineKeyboardButton("🔐 Reset Password", callback_data=f"{CB_ACTION_RESET_PWD}{instance_id}"),
        ],
        [
            InlineKeyboardButton("💿 Reinstall OS", callback_data=f"{CB_ACTION_REINSTALL}{instance_id}"),
            InlineKeyboardButton("🗑 Delete", callback_data=f"{CB_ACTION_DELETE}{instance_id}"),
        ],
        [InlineKeyboardButton("🌐 Open All TCP Ports", callback_data=f"{CB_SG_OPEN_TCP}{instance_id}")],
        [InlineKeyboardButton("🌐 Open All UDP Ports", callback_data=f"{CB_SG_OPEN_UDP}{instance_id}")],
        [InlineKeyboardButton("🌐 Open All TCP + UDP", callback_data=f"{CB_SG_OPEN_ALL}{instance_id}")],
        [InlineKeyboardButton("🔒 Revoke All TCP", callback_data=f"{CB_SG_REVOKE_TCP}{instance_id}")],
        [InlineKeyboardButton("🔒 Revoke All UDP", callback_data=f"{CB_SG_REVOKE_UDP}{instance_id}")],
        [InlineKeyboardButton("🔒 Revoke All TCP + UDP", callback_data=f"{CB_SG_REVOKE_ALL}{instance_id}")],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data=f"{CB_INSTANCE_REFRESH}{instance_id}"),
        ],
        [
            InlineKeyboardButton("🔙 Kembali", callback_data=CB_INSTANCES_LIST),
            InlineKeyboardButton("🏠 Home", callback_data=CB_HOME),
        ],
    ])


def confirm_action_keyboard(confirm_callback: str, cancel_callback: str = CB_HOME) -> InlineKeyboardMarkup:
    """Generic confirmation keyboard."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Ya, Lanjutkan", callback_data=confirm_callback)],
        [InlineKeyboardButton("❌ Batal", callback_data=cancel_callback)],
    ])


def confirm_dangerous_keyboard(confirm_callback: str, cancel_callback: str = CB_HOME) -> InlineKeyboardMarkup:
    """Dangerous action confirmation keyboard."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚠️ Saya Mengerti, Lanjutkan", callback_data=confirm_callback)],
        [InlineKeyboardButton("❌ Batal", callback_data=cancel_callback)],
    ])


def cancel_keyboard() -> InlineKeyboardMarkup:
    """Cancel-only keyboard."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Batal", callback_data=CB_CANCEL)],
    ])


def back_home_keyboard(back_callback: str = CB_BACK) -> InlineKeyboardMarkup:
    """Back + Home keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔙 Kembali", callback_data=back_callback),
            InlineKeyboardButton("🏠 Home", callback_data=CB_HOME),
        ]
    ])
