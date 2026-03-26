import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot, F, Router
from aiogram.enums import ChatMemberStatus, ContentType
from aiogram.filters import ChatMemberUpdatedFilter, IS_NOT_MEMBER, MEMBER
from aiogram.types import (
    CallbackQuery,
    ChatMemberUpdated,
    ChatPermissions,
    Message,
)

from captcha import CaptchaStore, build_keyboard
from config import (
    CAPTCHA_TIMEOUT,
    MSG_CAPTCHA,
    MSG_KICKED,
    MSG_NOT_FOR_YOU,
    MSG_WELCOME,
    MSG_WRONG,
    RESTRICT_UNTIL_EXTRA,
)

logger = logging.getLogger(__name__)

router = Router()
store = CaptchaStore()

# Track active timeout tasks so we can cancel on successful captcha
_timeout_tasks: dict[tuple[int, int], asyncio.Task] = {}  # type: ignore[type-arg]

# Per-user locks to prevent race conditions with concurrent messages
_user_locks: dict[tuple[int, int], asyncio.Lock] = {}


def _get_lock(chat_id: int, user_id: int) -> asyncio.Lock:
    key = (chat_id, user_id)
    if key not in _user_locks:
        _user_locks[key] = asyncio.Lock()
    return _user_locks[key]


MUTED = ChatPermissions(
    can_send_messages=False,
    can_send_audios=False,
    can_send_documents=False,
    can_send_photos=False,
    can_send_videos=False,
    can_send_video_notes=False,
    can_send_voice_notes=False,
    can_send_polls=False,
    can_send_other_messages=False,
    can_add_web_page_previews=False,
    can_change_info=False,
    can_invite_users=False,
    can_pin_messages=False,
    can_manage_topics=False,
)

UNMUTED = ChatPermissions(
    can_send_messages=True,
    can_send_audios=True,
    can_send_documents=True,
    can_send_photos=True,
    can_send_videos=True,
    can_send_video_notes=True,
    can_send_voice_notes=True,
    can_send_polls=True,
    can_send_other_messages=True,
    can_add_web_page_previews=True,
)


def _mention(user) -> str:  # noqa: ANN001
    name = user.full_name or user.first_name or "User"
    return f'<a href="tg://user?id={user.id}">{name}</a>'


async def _delete_message_safe(bot: Bot, chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass


async def _kick_user(bot: Bot, chat_id: int, user_id: int) -> None:
    """Kick without permanent ban — user can rejoin."""
    try:
        await bot.ban_chat_member(chat_id, user_id)
        await bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
    except Exception:
        logger.exception("Failed to kick user %s from chat %s", user_id, chat_id)


async def _timeout_handler(bot: Bot, chat_id: int, user_id: int) -> None:
    """Wait for captcha timeout, then kick the user."""
    await asyncio.sleep(CAPTCHA_TIMEOUT)
    captcha = store.remove(chat_id, user_id)
    if captcha is None:
        return  # already solved or removed

    # Delete captcha message
    if captcha.message_id:
        await _delete_message_safe(bot, chat_id, captcha.message_id)

    # Delete original user message (was kept while captcha was pending)
    if captcha.original_message_id:
        await _delete_message_safe(bot, chat_id, captcha.original_message_id)

    # Send kick message in the same thread (auto-delete after 10 sec)
    mention = _mention(type("U", (), {"id": user_id, "full_name": None, "first_name": str(user_id)})())
    try:
        kick_msg = await bot.send_message(
            chat_id,
            MSG_KICKED.format(mention=mention),
            parse_mode="HTML",
            message_thread_id=captcha.message_thread_id,
        )

        async def _delete_kick() -> None:
            await asyncio.sleep(10)
            await _delete_message_safe(bot, chat_id, kick_msg.message_id)

        asyncio.create_task(_delete_kick())
    except Exception:
        pass

    # Kick
    logger.info("User %s kicked from %s — captcha timeout", user_id, chat_id)
    await _kick_user(bot, chat_id, user_id)
    _timeout_tasks.pop((chat_id, user_id), None)


async def _send_captcha(
    bot: Bot,
    chat_id: int,
    user_id: int,
    user,
    message_thread_id: int | None = None,
    original_message_id: int | None = None,
) -> None:
    """Create and send a captcha challenge to a user."""
    # Mute with until_date as safety net for bot crashes
    until = datetime.now(timezone.utc) + timedelta(
        seconds=CAPTCHA_TIMEOUT + RESTRICT_UNTIL_EXTRA
    )
    try:
        await bot.restrict_chat_member(
            chat_id, user_id, permissions=MUTED, until_date=until
        )
    except Exception:
        logger.exception("Failed to restrict user %s", user_id)
        return

    # Create captcha
    captcha = store.create(chat_id, user_id)
    captcha.original_message_id = original_message_id
    captcha.message_thread_id = message_thread_id
    keyboard = build_keyboard(captcha)
    mention = _mention(user)
    text = MSG_CAPTCHA.format(
        mention=mention, emoji=captcha.correct_emoji, timeout=CAPTCHA_TIMEOUT
    )

    msg = await bot.send_message(
        chat_id,
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
        message_thread_id=message_thread_id,
        reply_to_message_id=original_message_id,
    )
    captcha.message_id = msg.message_id

    # Cancel previous timeout if exists (rejoining user)
    old_task = _timeout_tasks.pop((chat_id, user_id), None)
    if old_task:
        old_task.cancel()

    # Start timeout
    task = asyncio.create_task(_timeout_handler(bot, chat_id, user_id))
    _timeout_tasks[(chat_id, user_id)] = task


# --- Handler: new member joined (explicit join button) ---


@router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> MEMBER))
async def on_user_joined(event: ChatMemberUpdated, bot: Bot) -> None:
    user = event.new_chat_member.user

    # Skip bots
    if user.is_bot:
        return

    # Skip admins
    if event.new_chat_member.status in (
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.CREATOR,
    ):
        store.verify(event.chat.id, user.id)
        return

    # Already verified (e.g. passed captcha via comment before joining)
    if store.is_verified(event.chat.id, user.id):
        return

    await _send_captcha(bot, event.chat.id, user.id, user)


# --- Handler: captcha button pressed ---


@router.callback_query(F.data.startswith("cap:"))
async def on_captcha_button(callback: CallbackQuery, bot: Bot) -> None:
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer()
        return

    _, target_user_str, emoji = parts
    target_user_id = int(target_user_str)
    chat_id = callback.message.chat.id
    presser_id = callback.from_user.id

    # Only the target user can solve their captcha
    if presser_id != target_user_id:
        await callback.answer(MSG_NOT_FOR_YOU, show_alert=True)
        return

    captcha = store.get(chat_id, target_user_id)
    if captcha is None:
        await callback.answer()
        # Captcha expired or already solved — clean up message
        await _delete_message_safe(bot, chat_id, callback.message.message_id)
        return

    if emoji != captcha.correct_emoji:
        await callback.answer(MSG_WRONG, show_alert=False)
        return

    # Correct! Remove captcha and unmute
    store.remove(chat_id, target_user_id)
    store.verify(chat_id, target_user_id)
    logger.info("User %s verified in %s — captcha solved", target_user_id, chat_id)

    # Cancel timeout task
    task = _timeout_tasks.pop((chat_id, target_user_id), None)
    if task:
        task.cancel()

    # Unmute
    try:
        await bot.restrict_chat_member(
            chat_id, target_user_id, permissions=UNMUTED
        )
    except Exception:
        logger.exception("Failed to unmute user %s", target_user_id)

    # Delete captcha message (original user message stays)
    await _delete_message_safe(bot, chat_id, callback.message.message_id)

    # Send welcome in the same thread (auto-delete after 10 sec)
    mention = _mention(callback.from_user)
    try:
        welcome_msg = await bot.send_message(
            chat_id,
            MSG_WELCOME.format(mention=mention),
            parse_mode="HTML",
            message_thread_id=captcha.message_thread_id,
        )

        async def _delete_welcome() -> None:
            await asyncio.sleep(10)
            await _delete_message_safe(bot, chat_id, welcome_msg.message_id)

        asyncio.create_task(_delete_welcome())
    except Exception:
        pass

    await callback.answer()


# --- Handler: auto-delete join/leave service messages ---

_SERVICE_CLUTTER = {ContentType.NEW_CHAT_MEMBERS, ContentType.LEFT_CHAT_MEMBER}


@router.message(F.content_type.in_(_SERVICE_CLUTTER))
async def on_service_cleanup(message: Message, bot: Bot) -> None:
    """Auto-delete join/leave service messages to keep chat clean."""
    await _delete_message_safe(bot, message.chat.id, message.message_id)


# --- Handler: intercept messages from unverified users ---


@router.message()
async def on_message_filter(message: Message, bot: Bot) -> None:
    if message.from_user is None:
        return
    # Skip messages from channels (sender_chat = channel posting)
    if message.sender_chat:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    # Already verified — let through
    if store.is_verified(chat_id, user_id):
        return

    # Use lock to prevent race condition with concurrent messages
    async with _get_lock(chat_id, user_id):
        # Already has pending captcha — just delete the extra message
        if store.get(chat_id, user_id) is not None:
            await _delete_message_safe(bot, chat_id, message.message_id)
            return

        # First message from unverified user — check if they're an admin
        try:
            member = await bot.get_chat_member(chat_id, user_id)
            if member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
                store.verify(chat_id, user_id)
                return
        except Exception:
            logger.exception("Failed to check member status for %s", user_id)

        # Not verified, not admin — keep message, send captcha in the same thread
        logger.info(
            "Unverified user %s sent message in %s thread=%s — triggering captcha",
            user_id, chat_id, message.message_thread_id,
        )

        await _send_captcha(
            bot,
            chat_id,
            user_id,
            message.from_user,
            message_thread_id=message.message_thread_id,
            original_message_id=message.message_id,
        )
