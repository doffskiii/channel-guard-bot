import os

BOT_TOKEN = os.environ["BOT_TOKEN"]

# Captcha settings
CAPTCHA_TIMEOUT = 60  # seconds to solve captcha
RESTRICT_UNTIL_EXTRA = 30  # extra seconds for until_date safety margin
EMOJI_GRID_SIZE = 6  # total buttons (1 correct + 5 distractors)

# Emoji pool for captcha challenges
EMOJI_POOL = [
    "🐱", "🐶", "🐸", "🦊", "🐼", "🐨", "🦁", "🐯",
    "🐮", "🐷", "🐵", "🐔", "🦄", "🐙", "🦋", "🐢",
    "🍎", "🍕", "🎸", "🚀", "⚡", "🔥", "💎", "🎯",
    "🌈", "🌺", "🎲", "🏀", "🎭", "🍩", "🛸", "🧩",
]

# Messages (Russian)
MSG_CAPTCHA = "Привет, {mention}! Нажми на {emoji} чтобы подтвердить, что ты не бот.\nУ тебя {timeout} секунд."
MSG_WELCOME = "Добро пожаловать, {mention}!"
MSG_KICKED = "Время вышло — {mention} не прошёл проверку."
MSG_WRONG = "Неправильно, попробуй ещё раз."
MSG_NOT_FOR_YOU = "Эта капча не для тебя."
