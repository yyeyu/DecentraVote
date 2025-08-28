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
            [InlineKeyboardButton(text="Отменить создание", callback_data="cancel_voting"),]
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

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def create_vote_keyboard(answers: list[str], selected: set[int], multiple: bool) -> InlineKeyboardMarkup:
    # 1) Собираем все кнопки–ответы
    buttons: list[InlineKeyboardButton] = []
    for i, answer in enumerate(answers, start=1):
        mark = "✅ " if i in selected else ""
        buttons.append(
            InlineKeyboardButton(
                text=f"{mark}{i}. {answer}",
                callback_data=f"vote_{i}"
            )
        )

    # 2) Разбиваем на ряды по 3 кнопки
    rows: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(buttons), 3):
        rows.append(buttons[i : i + 3])

    # 3) Добавляем внизу кнопку «Подтвердить»
    rows.append([
        InlineKeyboardButton(
            text="✅ Подтвердить",
            callback_data="vote_confirm"
        )
    ])

    # 4) Возвращаем маппинг с явным inline_keyboard
    return InlineKeyboardMarkup(inline_keyboard=rows)
