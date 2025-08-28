import pytest
import os
import json
import time
from voting_service import VotingService

@pytest.fixture(scope="module")
def svc():
    module_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(module_dir, "..", ".."))
    abi = os.path.join(project_root, "blockchain", "contracts", "ContractABI.json")
    return VotingService(
        rpc_url="https://sepolia.infura.io/v3/9028a04a0daa4c60a27c3b93e664071a",
        contract_address="0x380A815DEB7a92ABC5C0583930AEBDe99546970C",
        abi_path=abi,
        secret_key="f3b1c9e2a8d6f7c4b5a3e9d0c1b2a3f4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f90a",
        admin_key="bc514d4c7375095a97071fe6e0a5ce4a1274bc5b45af5d8623e1ae5d3301ebbf"
    )

def get_blockchain_time(svc):
    block = svc.w3.eth.get_block('latest')
    return block['timestamp']

def create_and_wait_poll(svc, question="Q?", answers=["Yes", "No"], multiple=False, duration=120):
    current_blockchain_time = get_blockchain_time(svc)
    start = current_blockchain_time + 30

    print(f"\n\n\n\n\n\nDEBUG: blockchain time = {current_blockchain_time}, poll start = {start}")

    tx_hash = svc.create_poll(question, answers, multiple, start, duration)
    assert tx_hash.startswith("0x")

    poll_id = svc.get_last_poll_id()

    wait_time = max(0, start - get_blockchain_time(svc) + 1)
    if wait_time > 0:
        print(f"DEBUG: waiting for {wait_time} seconds until poll start")
        time.sleep(wait_time)

    return poll_id

def test_create_poll(svc):
    poll_id = create_and_wait_poll(svc, "Test question?", ["Yes", "No"])
    info = svc.get_poll_info(poll_id)
    assert info["question"] == "Test question?"
    assert info["answers"] == ["Yes", "No"]
    assert info["multiple_choices"] is False

def test_vote(svc):
    poll_id = create_and_wait_poll(svc)
    telegram_id = str(int(time.time()))
    answer_ids = [0]

    tx_hash = svc.vote(poll_id, answer_ids, telegram_id)
    assert tx_hash.startswith("0x")

    account = svc._derive_account(telegram_id)
    votes = svc.get_user_votes(poll_id, account.address)
    assert votes == answer_ids

def test_cancel_poll(svc):
    poll_id = create_and_wait_poll(svc)
    tx_hash = svc.cancel_poll(poll_id)
    assert tx_hash.startswith("0x")

    info = svc.get_poll_info(poll_id)
    assert info["canceled"] is True

def test_update_poll_schedule(svc):
    poll_id = create_and_wait_poll(svc)
    new_start = get_blockchain_time(svc) + 60
    new_duration = 300

    tx_hash = svc.update_poll_schedule(poll_id, new_start, new_duration)
    assert tx_hash.startswith("0x")

    info = svc.get_poll_info(poll_id)
    assert info["start_time"] == new_start
    assert info["end_time"] == new_start + new_duration
