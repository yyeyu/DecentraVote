from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram import F
from keyboards.creating_keyboards import (
    get_start_keyboard,
    get_add_options_keyboard,
    get_multiple_choice_keyboard,
    get_cancel_keyboard,
    get_finish_keyboard
)
from aiogram.fsm.context import FSMContext
from FSM.creating_states import VotingCreation
import re
from datetime import datetime
from blockchain.voting_service import VotingService
from aiogram.filters import StateFilter

DATE_TIME_PATTERN = re.compile(r'^\d{2}:\d{2} \d{2}\.\d{2}\.\d{4}$')

router = Router()

@router.callback_query(F.data == "cancel_voting")
async def cancel_voting(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text("❌ Создание голосования отменено.")
    await state.clear()

@router.message(F.text == "Создать голосование")
async def create_voting(message: Message, state: FSMContext):
    await state.clear()
    await state.set_data({"question": "", "options": [], "multiple_choice": False})
    await message.answer(
        "🗳️ <b>Создание голосования</b>\n\n"
        "Для создания голосования вы должны написать необходимые данные\n\n"
        "Нажмите кнопку ниже, чтобы начать.",
        reply_markup=get_start_keyboard()
    )

@router.callback_query(F.data == "start_voting_creation")
async def start_voting_creation(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text(
        "📝 Введите вопрос для голосования:",
        reply_markup=None
    )
    await state.set_state(VotingCreation.waiting_for_question)

@router.message(VotingCreation.waiting_for_question)
async def process_question(message: Message, state: FSMContext):
    if not message.text.strip():
        await message.answer("❌ Вопрос не может быть пустым. Введите вопрос снова.")
        return
    
    if len(message.text) > 256:
        await message.answer("❌ Вопрос слишком длинный (максимум 256 символов).")
        return

    await state.update_data(question=message.text)
    await message.answer(
        f"❓ Вопрос: <b>{message.text}</b>\n\n"
        "Теперь добавьте варианты ответа.",
        reply_markup=get_add_options_keyboard()
    )
    await state.set_state(VotingCreation.waiting_add_for_options)

@router.callback_query(F.data == "add_option", VotingCreation.waiting_add_for_options)
async def add_option(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text(
        "✍️ Введите новый вариант ответа:"
    )

@router.message(VotingCreation.waiting_add_for_options)
async def process_option(message: Message, state: FSMContext):
    if not message.text.strip():
        await message.answer("❌ Вариант не может быть пустым. Введите вариант снова.")
        return
    
    data = await state.get_data()
    options = data.get("options", [])

    if len(options) >= 10:
        await message.answer("❌ Достигнут лимит в 80 вариантов ответов.")
        return

    if len(message.text) > 100:
        await message.answer("❌ Вариант слишком длинный (максимум 100 символов).")
        return

    options.append(message.text)
    await state.update_data(options=options)

    formatted_options = "\n".join([f"{i+1}) {option}" for i, option in enumerate(options)])
    
    await message.answer(
        f"✅ Добавлен вариант: <b>{message.text}</b>\n\n"
        f"Текущие варианты:\n{formatted_options}",
        reply_markup=get_add_options_keyboard()
    )

@router.callback_query(F.data == "finish_options")
async def finish_options(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text(
        "🔢 Разрешить множественный выбор?",
        reply_markup=get_multiple_choice_keyboard()
    )
    await state.set_state(VotingCreation.waiting_for_multiple_choice)

@router.callback_query(VotingCreation.waiting_for_multiple_choice)
async def process_multiple_choice(callback_query: CallbackQuery, state: FSMContext):
    multiple_choice = callback_query.data.split("_")[-1] == "yes"
    await state.update_data(multiple_choice=multiple_choice)
    await callback_query.message.edit_text(
        f"✅ Множественный выбор: {'Да' if multiple_choice else 'Нет'}\n\n"
        "Введите время начала голосования (например, 12:00):",
        reply_markup=None
    )
    await state.set_state(VotingCreation.waiting_for_start_time)

@router.message(VotingCreation.waiting_for_start_time)
async def process_start_time(message: Message, state: FSMContext):
    user_input = message.text.strip()

    if not DATE_TIME_PATTERN.match(user_input):
        await message.answer(
            "❌ Некорректный формат!\n"
            "Введите время и дату в формате: <code>ЧЧ:ММ ДД.ММ.ГГГГ</code>\n"
            "Пример: <code>15:30 25.12.2026</code>",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    try:
        start_time = datetime.strptime(user_input, "%H:%M %d.%m.%Y")
    except ValueError:
        await message.answer(
            "❌ Ошибка в дате или времени!\n"
            "Проверьте, что дата и время указаны верно.",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    if start_time < datetime.now():
        await message.answer(
            "❌ Время уже прошло!\n"
            "Введите дату и время в будущем.",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    await state.update_data(start_time=user_input)
    await message.answer(
        f"✅ Время начала: {user_input}\n\n"
        "Введите длительность голосования (в часах):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(VotingCreation.waiting_for_duration)

@router.message(VotingCreation.waiting_for_duration)
async def process_duration(message: Message, state: FSMContext):
    try:
        duration = int(message.text)
        if duration <= 0:
            raise ValueError("Длительность должна быть положительным числом.")
    except ValueError as e:
        await message.answer(f"❌ {e}. Попробуйте снова.")
        return
    
    await state.update_data(duration=int(message.text))
    data = await state.get_data()
    await message.answer(
        f"🗳️ <b>Готово!</b>\n\n"
        f"Вопрос: {data['question']}\n"
        f"Варианты: {', '.join(data['options'])}\n"
        f"Множественный выбор: {'Да' if data['multiple_choice'] else 'Нет'}\n"
        f"Время начала: {data['start_time']}\n"
        f"Длительность: {data['duration']} часа(ов)",
        reply_markup=get_finish_keyboard()
    )
    await state.set_state(VotingCreation.waiting_for_confirmation)

@router.callback_query(StateFilter(VotingCreation.waiting_for_confirmation), F.data == "confirm_voting")
async def confirm_voting(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    data = await state.get_data()
    question = data.get("question")
    options = data.get("options")
    multiple_choice = data.get("multiple_choice")
    start_time = data.get("start_time")
    duration_hours = data.get("duration")
    try:
        voting_service = VotingService()
        poll_id = await voting_service.create_poll(
            question=question,
            options=options,
            multiple_choices=multiple_choice,
            start_time=start_time,
            duration_hours=duration_hours
        )
        options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])
        multiple_choice_text = "Да" if multiple_choice else "Нет"
        await callback_query.message.answer(
            f"✅ Голосование успешно создано!\n\n"
            f"ID голосования: {poll_id}\n"
            f"Вопрос: {question}\n"
            f"Варианты ответа:\n{options_text}\n"
            f"Множественный выбор: {multiple_choice_text}\n"
            f"Начало: {start_time}\n"
            f"Длительность: {duration_hours} часов"
        )
    except Exception as e:
        err_msg = str(e)
        if "ConnectionRefused" in err_msg or "Failed to establish a new connection" in err_msg:
            await callback_query.message.answer(
                "❌ Не удалось подключиться к RPC-нoде.\n"
                "Убедитесь, что вы запустили локальный блокчейн и правильно указали `RPC_URL` в .env."
            )
        elif "insufficient funds" in err_msg:
            await callback_query.message.answer(
                "❌ Недостаточно средств на счёте администратора для оплаты газа.\n"
                "Пожалуйста, пополните баланс или уменьшите `gas`/`gasPrice` в настройках."
            )
        else:
            from html import escape
            safe = escape(err_msg)
            await callback_query.message.answer(
                f"❌ Произошла ошибка при создании голосования:\n<pre>{safe}</pre>\n"
                "Пожалуйста, попробуйте создать голосование заново."
            )
    await state.clear()

@router.callback_query(F.data == "cancel_voting")
async def cancel_voting(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text(
        "❌ Создание голосования отменено."
    )
    await state.clear()