"""Tests for handler logic using mocked Bot API calls."""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("BOT_TOKEN", "test-token")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from handlers import on_captcha_button, on_message_filter, on_user_joined, store


def _make_user(user_id: int = 100, is_bot: bool = False, first_name: str = "Test") -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.is_bot = is_bot
    user.first_name = first_name
    user.full_name = first_name
    return user


def _make_chat_member_updated(
    user_id: int = 100,
    chat_id: int = 1,
    is_bot: bool = False,
    status: str = "member",
) -> MagicMock:
    event = MagicMock()
    user = _make_user(user_id, is_bot)
    event.new_chat_member.user = user
    event.new_chat_member.status = status
    event.chat.id = chat_id
    return event


def _make_callback_query(
    user_id: int, chat_id: int, data: str
) -> MagicMock:
    cb = MagicMock()
    cb.from_user = _make_user(user_id)
    cb.data = data
    cb.message.chat.id = chat_id
    cb.message.delete = AsyncMock()
    cb.answer = AsyncMock()
    return cb


def _make_message(user_id: int, chat_id: int) -> MagicMock:
    msg = MagicMock()
    msg.from_user = _make_user(user_id)
    msg.chat.id = chat_id
    msg.sender_chat = None
    msg.delete = AsyncMock()
    return msg


@pytest.fixture(autouse=True)
def _clean_store():
    """Clear captcha store between tests."""
    store._pending.clear()
    yield
    store._pending.clear()


class TestOnUserJoined:
    @pytest.mark.asyncio
    async def test_skip_bots(self) -> None:
        event = _make_chat_member_updated(is_bot=True)
        bot = AsyncMock()
        await on_user_joined(event, bot)
        bot.restrict_chat_member.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_admins(self) -> None:
        event = _make_chat_member_updated(status="administrator")
        bot = AsyncMock()
        await on_user_joined(event, bot)
        bot.restrict_chat_member.assert_not_called()

    @pytest.mark.asyncio
    async def test_mutes_and_sends_captcha(self) -> None:
        event = _make_chat_member_updated(user_id=200, chat_id=10)
        bot = AsyncMock()
        bot.send_message = AsyncMock(return_value=MagicMock(message_id=999))
        await on_user_joined(event, bot)

        # Verify restrict was called
        bot.restrict_chat_member.assert_called_once()
        call_args = bot.restrict_chat_member.call_args
        assert call_args[0][0] == 10  # chat_id
        assert call_args[0][1] == 200  # user_id

        # Verify captcha message sent
        bot.send_message.assert_called_once()

        # Verify captcha stored
        cap = store.get(10, 200)
        assert cap is not None
        assert cap.message_id == 999


class TestOnCaptchaButton:
    @pytest.mark.asyncio
    async def test_wrong_user_rejected(self) -> None:
        cap = store.create(chat_id=10, user_id=200)
        cb = _make_callback_query(user_id=999, chat_id=10, data=f"cap:200:{cap.correct_emoji}")
        bot = AsyncMock()
        await on_captcha_button(cb, bot)
        cb.answer.assert_called_once()
        assert "не к тебе" in cb.answer.call_args[0][0]
        # User should still be pending
        assert store.get(10, 200) is not None

    @pytest.mark.asyncio
    async def test_wrong_emoji(self) -> None:
        cap = store.create(chat_id=10, user_id=200)
        wrong = "🤖" if cap.correct_emoji != "🤖" else "👻"
        cb = _make_callback_query(user_id=200, chat_id=10, data=f"cap:200:{wrong}")
        bot = AsyncMock()
        await on_captcha_button(cb, bot)
        cb.answer.assert_called()
        # Still pending
        assert store.get(10, 200) is not None

    @pytest.mark.asyncio
    async def test_correct_emoji_unmutes(self) -> None:
        cap = store.create(chat_id=10, user_id=200)
        cap.message_id = 555
        cb = _make_callback_query(
            user_id=200, chat_id=10, data=f"cap:200:{cap.correct_emoji}"
        )
        bot = AsyncMock()
        bot.send_message = AsyncMock(return_value=MagicMock(message_id=777))
        await on_captcha_button(cb, bot)

        # Verify unmute
        bot.restrict_chat_member.assert_called_once()

        # Verify captcha removed
        assert store.get(10, 200) is None

        # Verify captcha message deleted
        cb.message.delete.assert_called_once()


class TestOnMessageFilter:
    @pytest.mark.asyncio
    async def test_deletes_message_from_pending_user(self) -> None:
        store.create(chat_id=10, user_id=200)
        msg = _make_message(user_id=200, chat_id=10)
        await on_message_filter(msg)
        msg.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_ignores_normal_user(self) -> None:
        msg = _make_message(user_id=300, chat_id=10)
        await on_message_filter(msg)
        msg.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_ignores_sender_chat(self) -> None:
        store.create(chat_id=10, user_id=200)
        msg = _make_message(user_id=200, chat_id=10)
        msg.sender_chat = MagicMock()  # channel posting
        await on_message_filter(msg)
        msg.delete.assert_not_called()
