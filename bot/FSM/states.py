from aiogram.fsm.state import StatesGroup, State

class VotingCreation(StatesGroup):
    waiting_for_question = State()
    waiting_add_for_options = State()
    waiting_for_multiple_choice = State()
    waiting_for_start_time = State()
    waiting_for_duration = State()
    waiting_for_confirmation = State()

class Info(StatesGroup):
    waiting_for_id_or_hash = State()

class VoteStates(StatesGroup):
    waiting_for_id_or_hash = State()
    waiting_for_vote = State()
    waiting_for_confirmation = State()