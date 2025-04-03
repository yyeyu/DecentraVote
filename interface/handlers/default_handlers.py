from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from keyboards.menu import get_menu_keyboard

router = Router()

@router.message(CommandStart())
async def command_start(message: Message):
    await message.answer(
        "👋 <b>Привет!</b>\n\n"
        "Добро пожаловать в <b>систему голосований на основе блокчейна.</b>\n\n"
        "Основные возможности:\n"
        "• Создавать защищенные голосования на базе блокчейна.\n"
        "• Участвовать в голосованиях, сохраняя анонимность и прозрачность.\n"
        "• Просматривать результаты в режиме реального времени, используя наш веб-обозреватель.\n\n"
        "🔒 Благодаря технологии блокчейн, все голоса надежно защищены от подделок и изменения.\n\n"
        "Чтобы начать, используйте одну из кнопок ниже:",
        reply_markup=get_menu_keyboard()
    )

@router.message()
async def unknown_message(message: Message):
    await message.answer(
        "<b>Неизвестная команда</b>\n\n"
        "Я не понимаю. Воспользуйтесь /start для получения информации"
    )
