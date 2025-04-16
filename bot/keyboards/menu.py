from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_menu_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Создать голосование")
            ]
        ],
        resize_keyboard=True
    )
    return keyboard