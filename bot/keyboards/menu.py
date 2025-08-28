from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_menu_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Создать голосование")
            ],
            [
                KeyboardButton(text="Проголосовать")
            ],
            [
                KeyboardButton(text="Открыть голосование"),
            ]
        ],
        resize_keyboard=True
    )
    return keyboard
