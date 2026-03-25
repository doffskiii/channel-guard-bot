import os
import sys

# Ensure config can be imported without BOT_TOKEN in tests
os.environ.setdefault("BOT_TOKEN", "test-token")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from captcha import CaptchaStore, build_keyboard
from config import EMOJI_GRID_SIZE, EMOJI_POOL


class TestCaptchaStore:
    def test_create_and_get(self) -> None:
        store = CaptchaStore()
        cap = store.create(chat_id=1, user_id=100)
        assert cap.chat_id == 1
        assert cap.user_id == 100
        assert cap.correct_emoji in EMOJI_POOL

        retrieved = store.get(1, 100)
        assert retrieved is cap

    def test_remove(self) -> None:
        store = CaptchaStore()
        store.create(chat_id=1, user_id=100)
        removed = store.remove(1, 100)
        assert removed is not None
        assert store.get(1, 100) is None

    def test_remove_nonexistent(self) -> None:
        store = CaptchaStore()
        assert store.remove(1, 999) is None

    def test_create_clears_old(self) -> None:
        store = CaptchaStore()
        cap1 = store.create(chat_id=1, user_id=100)
        cap2 = store.create(chat_id=1, user_id=100)
        assert cap1 is not cap2
        assert store.get(1, 100) is cap2

    def test_all_pending(self) -> None:
        store = CaptchaStore()
        store.create(1, 100)
        store.create(1, 200)
        store.create(2, 100)
        assert len(store.all_pending()) == 3

    def test_different_chats_isolated(self) -> None:
        store = CaptchaStore()
        store.create(1, 100)
        store.create(2, 100)
        store.remove(1, 100)
        assert store.get(1, 100) is None
        assert store.get(2, 100) is not None


class TestBuildKeyboard:
    def test_keyboard_structure(self) -> None:
        store = CaptchaStore()
        cap = store.create(1, 100)
        kb = build_keyboard(cap)
        rows = kb.inline_keyboard
        assert len(rows) == 2
        assert all(len(row) == 3 for row in rows)

    def test_correct_emoji_in_buttons(self) -> None:
        store = CaptchaStore()
        cap = store.create(1, 100)
        kb = build_keyboard(cap)
        all_emojis = [btn.text for row in kb.inline_keyboard for btn in row]
        assert cap.correct_emoji in all_emojis

    def test_total_buttons(self) -> None:
        store = CaptchaStore()
        cap = store.create(1, 100)
        kb = build_keyboard(cap)
        all_buttons = [btn for row in kb.inline_keyboard for btn in row]
        assert len(all_buttons) == EMOJI_GRID_SIZE

    def test_no_duplicate_emojis(self) -> None:
        store = CaptchaStore()
        cap = store.create(1, 100)
        kb = build_keyboard(cap)
        all_emojis = [btn.text for row in kb.inline_keyboard for btn in row]
        assert len(all_emojis) == len(set(all_emojis))

    def test_callback_data_format(self) -> None:
        store = CaptchaStore()
        cap = store.create(1, 100)
        kb = build_keyboard(cap)
        for row in kb.inline_keyboard:
            for btn in row:
                parts = btn.callback_data.split(":")
                assert len(parts) == 3
                assert parts[0] == "cap"
                assert parts[1] == "100"
                assert parts[2] in EMOJI_POOL
