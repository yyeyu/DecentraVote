from aiogram import Router, F
from aiogram.types import Message
from datetime import datetime
from dotenv import load_dotenv
from keyboards.creating_keyboards import get_cancel_keyboard
from keyboards.menu import get_menu_keyboard
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.markdown import hcode
from FSM.states import Info
from blockchain.voting_service import *
import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from aiogram.types import BufferedInputFile
import os
import html

router = Router()

load_dotenv()

RPC_URL = os.getenv("RPC_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
SECRET_KEY = os.getenv("SECRET_KEY")
ADMIN_KEY = os.getenv("ADMIN_KEY")
module_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(module_dir, "..", ".."))
ABI_PATH = os.path.join(project_root, "blockchain", "contracts", "ContractABI.json")
voting_service = VotingService(RPC_URL, CONTRACT_ADDRESS, ABI_PATH, SECRET_KEY, ADMIN_KEY)

def build_votes_chart(answers: list[str], results: list[int], poll_id: int, status_label: str) -> BufferedInputFile:
    labels = [(a if len(a) <= 24 else a[:21] + "…") for a in answers]

    fig = plt.figure(figsize=(8, 4.5))
    plt.bar(range(len(results)), results)
    plt.xticks(range(len(results)), labels, rotation=30, ha="right")
    plt.ylabel("Голоса")
    plt.title(f"Голоса по вариантам • #{poll_id} ({status_label})")
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=200)
    plt.close(fig)
    buf.seek(0)
    return BufferedInputFile(buf.getvalue(), filename=f"poll_{poll_id}_votes.png")

@router.message(F.text == "Открыть голосование")
async def open_poll_handler(message: Message, state: FSMContext):
    await message.answer(
        "🔍 Введите <b>ID</b> или <b>хеш транзакции</b> голосования, чтобы получить информацию.",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(Info.waiting_for_id_or_hash)

@router.message(Info.waiting_for_id_or_hash)
async def process_poll_identifier(message: Message, state: FSMContext):
    user_input = message.text.strip()
    await state.clear()

    try:
        poll_id = None

        if user_input.isdigit():
            poll_id = int(user_input)

        elif user_input.startswith("0x") and len(user_input) == 66 and all(c in "0123456789abcdefABCDEF" for c in user_input[2:]):
            tx_receipt = voting_service.w3.eth.get_transaction_receipt(user_input)
            logs = tx_receipt.get('logs', [])
            if not logs:
                raise ValueError("🚫 В транзакции нет логов. Возможно, это не создание голосования.")

            first_log = logs[0]
            topics = first_log.get('topics', [])
            if len(topics) < 2:
                raise ValueError("⚠️ Не удалось извлечь poll_id из логов.")

            poll_id_topic = topics[1]
            if isinstance(poll_id_topic, (bytes, bytearray)):
                poll_id = int.from_bytes(poll_id_topic[-32:], byteorder='big')
            else:
                poll_id = int(poll_id_topic, 16)

        else:
            raise ValueError("Введите корректный ID (число) или хэш (0x...)")

        try:
            info = voting_service.get_poll_info(poll_id)
        except Exception as inner:
            if "Poll does not exist" in str(inner):
                raise ValueError("Голосование с таким ID не найдено.")
            raise

        now_ts = int(datetime.now().timestamp())

        start_time = info['start_time']
        end_time = info['end_time']
        question = info['question']
        answers = info['answers']
        multiple = info['multiple_choices']
        canceled = info['canceled']
        creator = info['creator']

        print("\n\n\n\n", start_time, end_time, question, answers, multiple, canceled, creator)

        if canceled:
            status = "❌ Голосование отменено"
        elif now_ts < start_time:
            status = f"🕒 Ещё не началось: {datetime.fromtimestamp(start_time).strftime('%d.%m.%Y %H:%M:%S')}"
        elif now_ts > end_time:
            status = f"⏰ Завершено: {datetime.fromtimestamp(end_time).strftime('%d.%m.%Y %H:%M:%S')}"
        else:
            status = "✅ Активно"

        if canceled:
            results_text = "Пока недоступны (голосование отменено)"
        elif now_ts < start_time:
            results_text = "Пока недоступны (голосование ещё не началось)"
        else:
            try:
                results = voting_service.get_results(poll_id)

                if answers:
                    results_text = "\n".join(
                        f"• {html.escape(a)}: {v}" for a, v in zip(answers, results)
                    )
                    if not results_text.strip():
                        results_text = "Голоса ещё не поступили"
                else:
                    results_text = "Голоса ещё не поступили"

            except Exception as e:
                results_text = f"⚠️ Ошибка при получении результатов: {e}"

        msg = (
            f"<b>Голосование #{poll_id}</b>\n\n"
            f"📝 Вопрос: {html.escape(question)}\n"
            f"👤 Создатель: {hcode(creator)}\n"
            f"🔁 Множественный выбор: {'да' if multiple else 'нет'}\n"
            f"📊 Статус: {status}\n\n"
            f"<b>Варианты и результаты:</b>\n{results_text}"
        )

        await message.answer(msg, parse_mode="HTML", reply_markup=get_menu_keyboard())

        can_plot = True
        if canceled or now_ts < start_time:
            can_plot = False

        if can_plot:
            try:
                results = voting_service.get_results(poll_id)
                if not answers or len(results) != len(answers):
                    can_plot = False

                if can_plot:
                    if now_ts > end_time:
                        status_label = "Завершено"
                    else:
                        status_label = "Активно"

                    chart = build_votes_chart(answers, results, poll_id, status_label)
                    await message.answer_photo(
                        photo=chart,
                        caption="Диаграмма распределения голосов"
                    )
            except Exception as e:
                await message.answer(f"⚠️ Не удалось построить диаграмму: {e}")

    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}", reply_markup=get_menu_keyboard())
