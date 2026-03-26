import random
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import EMOJI_GRID_SIZE, EMOJI_POOL

DB_PATH = Path(__file__).parent / "data" / "guard.db"


@dataclass
class PendingCaptcha:
    user_id: int
    chat_id: int
    correct_emoji: str
    message_id: int | None = None
    original_message_id: int | None = None
    message_thread_id: int | None = None
    created_at: float = field(default_factory=time.time)


class CaptchaStore:
    """SQLite-backed store for verified users, in-memory for pending captchas."""

    def __init__(self) -> None:
        self._pending: dict[tuple[int, int], PendingCaptcha] = {}  # (chat_id, user_id)
        self._db = self._init_db()
        self._verified_cache: set[tuple[int, int]] = self._load_verified()

    def _init_db(self) -> sqlite3.Connection:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.execute(
            """CREATE TABLE IF NOT EXISTS verified (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                verified_at REAL NOT NULL,
                PRIMARY KEY (chat_id, user_id)
            )"""
        )
        conn.commit()
        return conn

    def _load_verified(self) -> set[tuple[int, int]]:
        rows = self._db.execute("SELECT chat_id, user_id FROM verified").fetchall()
        return {(r[0], r[1]) for r in rows}

    def create(self, chat_id: int, user_id: int) -> PendingCaptcha:
        self.remove(chat_id, user_id)
        correct = random.choice(EMOJI_POOL)
        captcha = PendingCaptcha(user_id=user_id, chat_id=chat_id, correct_emoji=correct)
        self._pending[(chat_id, user_id)] = captcha
        return captcha

    def get(self, chat_id: int, user_id: int) -> PendingCaptcha | None:
        return self._pending.get((chat_id, user_id))

    def remove(self, chat_id: int, user_id: int) -> PendingCaptcha | None:
        return self._pending.pop((chat_id, user_id), None)

    def all_pending(self) -> list[PendingCaptcha]:
        return list(self._pending.values())

    def verify(self, chat_id: int, user_id: int) -> None:
        self._verified_cache.add((chat_id, user_id))
        self._db.execute(
            "INSERT OR IGNORE INTO verified (chat_id, user_id, verified_at) VALUES (?, ?, ?)",
            (chat_id, user_id, time.time()),
        )
        self._db.commit()

    def is_verified(self, chat_id: int, user_id: int) -> bool:
        return (chat_id, user_id) in self._verified_cache

    def unverify(self, chat_id: int, user_id: int) -> None:
        self._verified_cache.discard((chat_id, user_id))
        self._db.execute(
            "DELETE FROM verified WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id),
        )
        self._db.commit()


def build_keyboard(captcha: PendingCaptcha) -> InlineKeyboardMarkup:
    """Build a 2x3 grid of emoji buttons with one correct answer."""
    correct = captcha.correct_emoji
    distractors = [e for e in EMOJI_POOL if e != correct]
    chosen = random.sample(distractors, EMOJI_GRID_SIZE - 1)
    all_emojis = [correct] + chosen
    random.shuffle(all_emojis)

    buttons = [
        InlineKeyboardButton(
            text=emoji,
            callback_data=f"cap:{captcha.user_id}:{emoji}",
        )
        for emoji in all_emojis
    ]
    # 2 rows x 3 columns
    keyboard = [buttons[i : i + 3] for i in range(0, len(buttons), 3)]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
