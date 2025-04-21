from web3 import Web3
from eth_account import Account
import json
import os
from dotenv import load_dotenv
import hmac, hashlib

load_dotenv()

class VotingContract:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
        
        # Загрузка ABI контракта (путь выстраиваем относительно расположения этого файла)
        module_dir = os.path.dirname(__file__)
        project_root = os.path.abspath(os.path.join(module_dir, "..", ".."))
        abi_path = os.path.join(project_root, "blockchain", "artifacts", "contracts", "voting.sol", "Voting.json")
        with open(abi_path, "r") as f:
            contract_json = json.load(f)
            self.abi = contract_json["abi"]
        
        self.contract = self.w3.eth.contract(
            address=os.getenv("CONTRACT_ADDRESS"),
            abi=self.abi
        )
        
        self.admin_key = os.getenv("PRIVATE_KEY")
        self.admin_account = Account.from_key(self.admin_key)
        self.secret_key = os.getenv("SECRET_KEY")

    def derive_private_key(self, telegram_id: str) -> str:
        digest = hmac.new(self.secret_key.encode(), telegram_id.encode(), hashlib.sha256).digest()
        return "0x" + digest.hex()

    async def create_poll(self, question: str, answers: list, multiple_choices: bool, duration: int):
        tx = self.contract.functions.createPoll(
            question,
            answers,
            multiple_choices,
            duration
        ).build_transaction({
            'from': self.admin_account.address,
            'nonce': self.w3.eth.get_transaction_count(self.admin_account.address),
            'gas': 2000000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.admin_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)

    async def vote(self, telegram_id: str, poll_id: int, answer_ids: list):
        user_key = self.derive_private_key(telegram_id)
        user_account = Account.from_key(user_key)
        
        tx = self.contract.functions.vote(
            poll_id,
            answer_ids
        ).build_transaction({
            'from': user_account.address,
            'nonce': self.w3.eth.get_transaction_count(user_account.address),
            'gas': 2000000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        signed_tx = self.w3.eth.account.sign_transaction(tx, user_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)

    async def get_poll_info(self, poll_id: int):
        return self.contract.functions.getPollInfo(poll_id).call()

    async def get_results(self, poll_id: int):
        return self.contract.functions.getResults(poll_id).call()

    async def get_active_polls(self):
        return self.contract.functions.getActivePolls().call()

    async def get_user_votes(self, poll_id: int, user_address: str):
        return self.contract.functions.getUserVotes(poll_id, user_address).call()
    