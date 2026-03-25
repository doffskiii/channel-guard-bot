import random
import time
from dataclasses import dataclass, field

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import EMOJI_GRID_SIZE, EMOJI_POOL


@dataclass
class PendingCaptcha:
    user_id: int
    chat_id: int
    correct_emoji: str
    message_id: int | None = None
    created_at: float = field(default_factory=time.time)


class CaptchaStore:
    """In-memory store for pending captcha challenges."""

    def __init__(self) -> None:
        self._pending: dict[tuple[int, int], PendingCaptcha] = {}  # (chat_id, user_id)

    def create(self, chat_id: int, user_id: int) -> PendingCaptcha:
        # Clear old entry if exists (e.g. user rejoined)
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
