from .contract import VotingContract
import asyncio
from datetime import datetime

class VotingService:
    def __init__(self):
        self.vc = VotingContract()

    async def create_poll(self, question: str, options: list, multiple_choices: bool, start_time: str, duration_hours: int) -> int:
        dt = datetime.strptime(start_time, "%H:%M %d.%m.%Y")
        now = datetime.now()
        if dt > now:
            wait_seconds = (dt - now).total_seconds()
            await asyncio.sleep(wait_seconds)
        duration_seconds = duration_hours * 3600
        receipt = await self.vc.create_poll(
            question,
            options,
            multiple_choices,
            duration_seconds
        )
        try:
            events = self.vc.contract.events.PollCreated().process_receipt(receipt)
        except Exception:
            try:
                events = self.vc.contract.events.PollCreated().processReceipt(receipt)
            except Exception:
                next_id = self.vc.contract.functions.nextPollID().call()
                return next_id - 1
        if not events:
            raise Exception("PollCreated event не найден в транзакции")
        poll_id = events[0]['args'].get('pollID') if isinstance(events[0]['args'], dict) else events[0]['args'].pollID
        return poll_id 