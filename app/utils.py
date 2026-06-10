"""
Utility module.
Helper functions for loading states, formatting messages, etc.
"""

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from app.states import CB_HOME, CB_BACK


# ==================== Loading / Status Helpers ====================

async def show_loading(query, text: str = "⏳ Memproses..."):
    """Show loading state by editing the message."""
    try:
        await query.edit_message_text(
            text=text,
            parse_mode="HTML"
        )
    except Exception:
        pass


async def show_success(
    query,
    text: str,
    keyboard: InlineKeyboardMarkup = None
):
    """Show success message with optional keyboard."""
    if keyboard is None:
        keyboard = get_back_home_keyboard()
    try:
        await query.edit_message_text(
            text=f"✅ {text}",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception:
        pass


async def show_error(
    query,
    error: str,
    keyboard: InlineKeyboardMarkup = None
):
    """Show error message with optional keyboard."""
    if keyboard is None:
        keyboard = get_back_home_keyboard()
    try:
        await query.edit_message_text(
            text=f"❌ <b>Error:</b> {error}",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception:
        pass


async def send_loading(message, text: str = "⏳ Memproses..."):
    """Send a new loading message (for message handlers)."""
    return await message.reply_text(text, parse_mode="HTML")


async def edit_loading(message, text: str, keyboard=None):
    """Edit an existing message with result."""
    try:
        await message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception:
        pass


# ==================== Keyboard Helpers ====================

def get_back_home_keyboard(back_callback: str = CB_BACK) -> InlineKeyboardMarkup:
    """Get standard Back + Home keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔙 Kembali", callback_data=back_callback),
            InlineKeyboardButton("🏠 Home", callback_data=CB_HOME),
        ]
    ])


def get_home_keyboard() -> InlineKeyboardMarkup:
    """Get Home-only keyboard."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Home", callback_data=CB_HOME)]
    ])


# ==================== Formatting Helpers ====================

def format_status_emoji(status: str) -> str:
    """Format instance status with emoji."""
    status_map = {
        "Running": "🟢 Running",
        "Stopped": "🔴 Stopped",
        "Starting": "🟡 Starting",
        "Stopping": "🟡 Stopping",
        "Pending": "🟡 Pending",
    }
    return status_map.get(status, f"⚪ {status}")


def format_instance_type_label(os_type: str) -> str:
    """Label instance as VPS or RDP based on OS type."""
    if os_type and "windows" in os_type.lower():
        return "🖥 RDP"
    return "🐧 VPS"


def truncate_text(text: str, max_length: int = 30) -> str:
    """Truncate text to max length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


# ==================== Context Data Helpers ====================

def set_user_data(context: ContextTypes.DEFAULT_TYPE, key: str, value):
    """Set a value in user_data."""
    context.user_data[key] = value


def get_user_data(context: ContextTypes.DEFAULT_TYPE, key: str, default=None):
    """Get a value from user_data."""
    return context.user_data.get(key, default)


def clear_user_data(context: ContextTypes.DEFAULT_TYPE):
    """Clear all user_data."""
    context.user_data.clear()


# Context keys
CTX_CURRENT_ACCOUNT_ID = "current_account_id"
CTX_CURRENT_ACCOUNT_NAME = "current_account_name"
CTX_CURRENT_REGION = "current_region"
CTX_CURRENT_INSTANCE_ID = "current_instance_id"
CTX_TEMP_ACCOUNT_NAME = "temp_account_name"
CTX_TEMP_KEY_ID = "temp_key_id"
CTX_TEMP_KEY_SECRET = "temp_key_secret"
CTX_TEMP_PASSWORD = "temp_password"
CTX_TEMP_IMAGE_ID = "temp_image_id"


# ==================== Validation Helpers ====================

def validate_alibaba_password(password: str) -> tuple[bool, str]:
    """
    Validate password for Alibaba ECS instance.
    Rules:
    - 8-30 characters
    - Must contain at least 3 of: uppercase, lowercase, digit, special char
    - Special chars: ( ) ` ~ ! @ # $ % ^ & * - _ + = | { } [ ] : ; ' < > , . ? /
    """
    if len(password) < 8 or len(password) > 30:
        return False, "Password harus 8-30 karakter."

    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    special_chars = set("()` ~!@#$%^&*-_+=|{}[]:;'<>,.?/")
    has_special = any(c in special_chars for c in password)

    complexity = sum([has_upper, has_lower, has_digit, has_special])
    if complexity < 3:
        return False, (
            "Password harus mengandung minimal 3 dari: "
            "huruf besar, huruf kecil, angka, karakter spesial."
        )

    return True, "OK"
