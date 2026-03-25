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

# Messages — tone: русский фейсер из московского клуба 90-х
MSG_CAPTCHA = "Слышь, {mention}, ты кто по жизни? Тыкни на {emoji} и докажи что не бот. У тебя {timeout} секунд, потом на выход."
MSG_WELCOME = "Нормально, {mention}, заходи. Веди себя ровно."
MSG_KICKED = "{mention} не шарит — на выход."
MSG_WRONG = "Мимо, братан. Давай ещё раз, глаза разуй."
MSG_NOT_FOR_YOU = "Э, не лезь, это не твоя тема."
