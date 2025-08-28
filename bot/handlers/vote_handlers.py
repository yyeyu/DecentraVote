from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime
from dotenv import load_dotenv
import os, html

from keyboards.creating_keyboards import create_vote_keyboard, get_cancel_keyboard
from keyboards.menu import get_menu_keyboard
from FSM.states import VoteStates
from blockchain.voting_service import VotingService

load_dotenv()
RPC_URL = os.getenv("RPC_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
SECRET_KEY = os.getenv("SECRET_KEY")
ADMIN_KEY = os.getenv("ADMIN_KEY")
module_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(module_dir, "..", ".."))
ABI_PATH = os.path.join(project_root, "blockchain", "contracts", "ContractABI.json")

voting_service = VotingService(RPC_URL, CONTRACT_ADDRESS, ABI_PATH, SECRET_KEY, ADMIN_KEY)
router = Router()


@router.message(F.text == "Проголосовать")
async def start_vote(message: Message, state: FSMContext):
    await message.answer(
        "Введите <b>ID</b> или <b>хеш транзакции</b> голосования:",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(VoteStates.waiting_for_id_or_hash)


@router.message(VoteStates.waiting_for_id_or_hash)
async def process_poll_identifier(message: Message, state: FSMContext):
    user_input = message.text.strip()

    try:
        if user_input.isdigit():
            poll_id = int(user_input)

        elif user_input.startswith("0x") and len(user_input) == 66 and all(c in "0123456789abcdefABCDEF" for c in user_input[2:]):
            receipt = voting_service.w3.eth.get_transaction_receipt(user_input)
            events = voting_service.contract.events.PollCreated().process_receipt(receipt)
            if not events:
                raise ValueError("🚫 В транзакции нет события создания голосования (PollCreated).")
            poll_id = events[0]["args"]["id"]

        else:
            raise ValueError("❌ Введите корректный ID (число) или хэш (0x...)")

    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}", reply_markup=get_menu_keyboard())
        return

    try:
        info = voting_service.get_poll_info(poll_id)
    except Exception as e:
        await message.answer(f"❌ Не удалось получить голосование #{poll_id}: {e}", reply_markup=get_menu_keyboard())
        return

    start_ts = info["start_time"]
    end_ts   = info["end_time"]
    if start_ts > 10**12: start_ts //= 1000
    if end_ts   > 10**12: end_ts   //= 1000
    now_ts = int(datetime.now().timestamp())

    if info["canceled"]:
        await message.answer("❌ Голосование отменено, участие невозможно.", reply_markup=get_menu_keyboard())
        await state.clear()
        return
    if now_ts < start_ts:
        await message.answer(
            f"🕒 Голосование ещё не началось.\nНачнётся: {datetime.utcfromtimestamp(start_ts):%d.%m.%Y %H:%M:%S}",
            reply_markup=get_menu_keyboard()
        )
        await state.clear()
        return
    if now_ts > end_ts:
        await message.answer(
            f"⏰ Голосование завершено.\nЗавершилось: {datetime.utcfromtimestamp(end_ts):%d.%m.%Y %H:%M:%S}",
            reply_markup=get_menu_keyboard()
        )
        await state.clear()
        return

    answers = info["answers"]
    if not answers:
        await message.answer("❌ В этом голосовании нет вариантов.", reply_markup=get_menu_keyboard())
        await state.clear()
        return

    await state.update_data(
        poll_id=poll_id,
        answers=answers,
        multiple=info["multiple_choices"],
        selected=set()
    )
    keyboard = create_vote_keyboard(answers, selected=set(), multiple=info["multiple_choices"])
    await message.answer("Выберите вариант(ы):", reply_markup=keyboard)
    await state.set_state(VoteStates.waiting_for_vote)


@router.callback_query(F.data.startswith("vote_"), VoteStates.waiting_for_vote)
async def vote_option_callback(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected", set())
    answers  = data["answers"]
    multiple = data["multiple"]
    poll_id  = data["poll_id"]

    key = callback.data.removeprefix("vote_")

    if key == "confirm":
        if not selected:
            await callback.answer("Выберите хотя бы один вариант!", show_alert=True)
            return

        answer_ids = [i - 1 for i in selected]
        try:
            tx_hash = voting_service.vote(poll_id, answer_ids, str(callback.from_user.id))
        except Exception as e:
            await callback.answer(f"❌ Ошибка при отправке голоса: {e}", show_alert=True)
            return

        await callback.message.edit_text(
            f"✅ Ваш голос учтён!\nTx: <code>0x{tx_hash}</code>",
            parse_mode="HTML",
            reply_markup=None
        )
        await state.clear()
        return

    try:
        idx = int(key)
    except ValueError:
        await callback.answer("❌ Неверный вариант", show_alert=True)
        return

    if not (1 <= idx <= len(answers)):
        await callback.answer("❌ Такого варианта нет", show_alert=True)
        return

    if multiple:
        if idx in selected:
            selected.remove(idx)
        else:
            selected.add(idx)
    else:
        selected = {idx}

    await state.update_data(selected=selected)
    keyboard = create_vote_keyboard(answers, selected, multiple)
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer()
