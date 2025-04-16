from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_start_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Начать создание", callback_data="start_voting_creation")]
        ]
    )
    return keyboard

def get_add_options_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Добавить вариант", callback_data="add_option"),
             InlineKeyboardButton(text="Завершить добавление", callback_data="finish_options")],
            [InlineKeyboardButton(text="Отменить создание", callback_data="cancel_voting")]
        ]
    )
    return keyboard

def get_multiple_choice_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="multiple_choice_yes"), 
             InlineKeyboardButton(text="Нет", callback_data="multiple_choice_no")],
            [InlineKeyboardButton(text="Отменить создание", callback_data="cancel_voting")]
        ]
    )
    return keyboard

def get_cancel_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Отменить создание", callback_data="cancel_voting")]
        ]
    )

def get_finish_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подтвердить", callback_data="confirm_voting")],
            [InlineKeyboardButton(text="Отменить", callback_data="cancel_voting")]
        ]
    )
    return keyboard
