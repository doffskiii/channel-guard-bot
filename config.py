import os

BOT_TOKEN = os.environ["BOT_TOKEN"]

# Captcha settings
CAPTCHA_TIMEOUT = 120  # seconds to solve captcha
RESTRICT_UNTIL_EXTRA = 60  # extra seconds for until_date safety margin
EMOJI_GRID_SIZE = 6  # total buttons (1 correct + 5 distractors)

# Emoji pool for captcha challenges
EMOJI_POOL = [
    "🐱", "🐶", "🐸", "🦊", "🐼", "🐨", "🦁", "🐯",
    "🐮", "🐷", "🐵", "🐔", "🦄", "🐙", "🦋", "🐢",
    "🍎", "🍕", "🎸", "🚀", "⚡", "🔥", "💎", "🎯",
    "🌈", "🌺", "🎲", "🏀", "🎭", "🍩", "🛸", "🧩",
]

# Messages — tone: вежливый но твёрдый фейсконтрольщик
MSG_CAPTCHA = "{mention}, привет. Нажми на {emoji}, пожалуйста. У тебя {timeout} секунд."
MSG_WELCOME = "{mention}, проходи. Веди себя ровно."
MSG_KICKED = "{mention}, к сожалению сегодня пройти не получится."
MSG_WRONG = "Не то. Попробуй ещё раз."
MSG_NOT_FOR_YOU = "Это не к тебе, друг."
