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
from FSM.states import VotingCreation
import re
from datetime import datetime
from aiogram.filters import StateFilter
from dotenv import load_dotenv
from blockchain.voting_service import *
import html

load_dotenv()

RPC_URL = os.getenv("RPC_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
SECRET_KEY = os.getenv("SECRET_KEY")
ADMIN_KEY = os.getenv("ADMIN_KEY")
module_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(module_dir, "..", ".."))
ABI_PATH = os.path.join(project_root, "blockchain", "contracts", "ContractABI.json")
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
        "Введите время начала голосования (формат: ЧЧ:ММ ДД.ММ.ГГГГ):",
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
        "Введите длительность голосования (в минутах):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(VotingCreation.waiting_for_duration)

@router.message(VotingCreation.waiting_for_duration)
async def process_duration(message: Message, state: FSMContext):
    try:
        duration_minutes = int(message.text.strip())
        
        if duration_minutes < 1:
            await message.answer(
                "❌ Минимальная длительность - 1 минута\n"
                "Попробуйте снова:",
                reply_markup=None
            )
            return
            
        if duration_minutes > 525600:
            await message.answer(
                "❌ Максимальная длительность - 525600 минут (365 дней)\n"
                "Попробуйте снова:",
                reply_markup=None
            )
            return

        duration_seconds = duration_minutes * 60
        await state.update_data({
            'duration': duration_minutes,  
            'duration_seconds': duration_seconds  
        })

        data = await state.get_data()
        
        days = duration_minutes // 1440
        hours = (duration_minutes % 1440) // 60
        minutes = duration_minutes % 60
        
        duration_display = []
        if days > 0:
            duration_display.append(f"{days} дн.")
        if hours > 0:
            duration_display.append(f"{hours} ч.")
        if minutes > 0 or not duration_display:
            duration_display.append(f"{minutes} мин.")
        
        await message.answer(
            f"🗳️ <b>Параметры голосования</b>\n\n"
            f"• Вопрос: {data['question']}\n"
            f"• Варианты: {', '.join(data['options'])}\n"
            f"• Множественный выбор: {'Да' if data['multiple_choice'] else 'Нет'}\n"
            f"• Начало: {data['start_time']}\n"
            f"• Длительность: {' '.join(duration_display)} ({duration_minutes} минут)",
            reply_markup=get_finish_keyboard(),
            parse_mode="HTML"
        )
        
        await state.set_state(VotingCreation.waiting_for_confirmation)

    except ValueError:
        await message.answer(
            "❌ Нужно ввести целое число минут (от 1 до 525600)\n"
            "Примеры:\n"
            "• 60 (1 час)\n"
            "• 1440 (1 день)\n"
            "• 10080 (1 неделя)",
            reply_markup=None
        )

@router.callback_query(StateFilter(VotingCreation.waiting_for_confirmation), F.data == "confirm_voting")
async def confirm_voting(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text("⏳ Подождите, идет загрузка голосования в блокчейн…\nОбычно это занимает 10-30 секунд.")

    data = await state.get_data()
    
    try:
        voting_service = VotingService(RPC_URL, CONTRACT_ADDRESS, ABI_PATH, SECRET_KEY, ADMIN_KEY)
        w3 = voting_service.w3

        required_fields = ['question', 'options', 'multiple_choice', 'start_time', 'duration_seconds']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Отсутствует обязательное поле: {field}")

        question = data["question"]
        answers = data["options"]
        multiple_choices = bool(data["multiple_choice"])
        duration_seconds = int(data["duration_seconds"])
        raw_start_time = data["start_time"]
        
        parsed_time = datetime.strptime(raw_start_time, "%H:%M %d.%m.%Y")
        start_time = int(parsed_time.timestamp())

        current_block = w3.eth.get_block('latest')
        current_time = current_block.timestamp
        time_diff = start_time - current_time

        if time_diff <= 0:
            raise ValueError(
                f"Время начала должно быть в будущем\n"
                f"• Текущее время блока: {current_time} ({datetime.fromtimestamp(current_time)})\n"
                f"• Указанное время: {start_time} ({datetime.fromtimestamp(start_time)})\n"
                f"• Разница: {time_diff} секунд"
            )

        receipt = voting_service.create_poll(
            question=question,
            answers=answers,
            multiple=multiple_choices,
            start=start_time,
            duration=duration_seconds
        )

        duration_minutes = duration_seconds // 60
        duration_hours = duration_minutes // 60
        duration_days = duration_hours // 24

        duration_str = []
        if duration_days > 0:
            duration_str.append(f"{duration_days} д.")
        if duration_hours % 24 > 0:
            duration_str.append(f"{duration_hours % 24} ч.")
        if duration_minutes % 60 > 0:
            duration_str.append(f"{duration_minutes % 60} мин.")

        await callback_query.message.edit_text(
            f"✅ <b>Голосование создано успешно!</b>\n\n"
            f"▸ Вопрос: {html.escape(question)}\n"
            f"▸ Варианты: {', '.join(html.escape(a) for a in answers)}\n"
            f"▸ Длительность: {' '.join(duration_str)}\n"
            f"▸ Начало: {parsed_time.strftime('%H:%M %d.%m.%Y')}\n\n"
            f"TX Hash: <code>0x{receipt}</code>",
            parse_mode="HTML",
            reply_markup=None
        )

    except ValueError as ve:
        await callback_query.message.edit_text(
            f"❌ <b>Ошибка валидации:</b>\n{html.escape(str(ve))}",
            parse_mode="HTML"
        )
    except Exception as e:
        error_msg = f"❌ <b>Критическая ошибка:</b>\n{html.escape(str(e))}"
        
        if hasattr(e, 'args') and e.args:
            error_details = "\n".join([html.escape(str(arg)) for arg in e.args if arg])
            if error_details:
                error_msg += f"\n\n<code>{error_details}</code>"
        
        await callback_query.message.edit_text(
            error_msg,
            parse_mode="HTML"
        )

    finally:
        await state.clear()

@router.callback_query(F.data == "cancel_voting")
async def cancel_voting(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text(
        "❌ Создание голосования отменено."
    )
    await state.clear()