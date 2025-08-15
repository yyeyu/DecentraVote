import os
import json
import hmac
import hashlib
import logging
from web3 import Web3
from eth_account import Account
from eth_keys.constants import SECPK1_N
from eth_utils import big_endian_to_int

# Logging setup
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

class VotingService:
    CHAIN_ID = 11155111
    MIN_FUND_WEI = Web3.to_wei(0.001, "ether")

    def __init__(self, rpc_url: str, contract_address: str,
                 abi_path: str, secret_key: str, admin_key: str):
        logger.debug("Initializing Web3 provider to %s", rpc_url)
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            logger.error("Failed to connect to RPC")
            raise ConnectionError("RPC connection failed")

        logger.debug("Loading ABI from %s", abi_path)
        with open(abi_path, 'r') as f:
            abi_json = json.load(f)
            self.abi = abi_json if isinstance(abi_json, list) else abi_json['abi']
        self.contract = self.w3.eth.contract(address=contract_address, abi=self.abi)

        self.secret_key = secret_key
        self.admin_account = Account.from_key(admin_key)
        logger.debug("Admin account loaded: %s", self.admin_account.address)

    def _derive_account(self, telegram_id: str) -> Account:
        digest = hmac.new(self.secret_key.encode(), telegram_id.encode(), hashlib.sha256).digest()
        key_int = big_endian_to_int(digest) % SECPK1_N
        acct = Account.from_key(key_int.to_bytes(32, 'big'))
        logger.debug("Derived account: %s", acct.address)
        return acct

    def _ensure_funded(self, user_addr: str):
        balance = self.w3.eth.get_balance(user_addr)
        if balance < self.MIN_FUND_WEI:
            logger.debug("Balance %s wei is below %s wei, topping up...", balance, self.MIN_FUND_WEI)
            tx = {
                "to": user_addr,
                "value": self.MIN_FUND_WEI,
                "chainId": self.CHAIN_ID,
                "gas": 21000,
                "maxPriorityFeePerGas": self.w3.eth.max_priority_fee,
                "maxFeePerGas": self.w3.eth.get_block("latest")["baseFeePerGas"]
                                  + self.w3.eth.max_priority_fee,
                "nonce": self.w3.eth.get_transaction_count(
                    self.admin_account.address, "pending"
                ),
            }
            signed = self.admin_account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            logger.debug("Funding tx sent: %s", tx_hash.hex())
            self.w3.eth.wait_for_transaction_receipt(tx_hash)
            logger.debug("Funding tx confirmed")

    def _send(self, fn_call, account: Account) -> str:
        logger.debug("Preparing transaction for account %s", account.address)
        gas_est = fn_call.estimate_gas({'from': account.address})
        latest = self.w3.eth.get_block('latest')
        base_fee = latest['baseFeePerGas']
        tip = self.w3.eth.max_priority_fee
        nonce = self.w3.eth.get_transaction_count(account.address, 'pending')

        tx = fn_call.build_transaction({
            'chainId': self.CHAIN_ID,
            'from': account.address,
            'nonce': nonce,
            'gas': gas_est + 10000,
            'maxPriorityFeePerGas': tip,
            'maxFeePerGas': base_fee + tip,
        })
        signed = account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        logger.debug("Sent tx, hash: %s", tx_hash.hex())
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        logger.debug("Transaction receipt status=%s", receipt.status)
        if receipt.status == 0:
            logger.error("Transaction reverted: %s", tx_hash.hex())
            raise RuntimeError("Transaction reverted")
        return tx_hash.hex()

    def create_poll(self, question: str, answers: list, multiple: bool,
                    start: int, duration: int) -> str:
        qb = question.encode('utf-8')[:256]
        ab = [a.encode('utf-8')[:128] for a in answers]
        fn = self.contract.functions.createPoll(qb, ab, multiple, start, duration)
        return self._send(fn, self.admin_account)

    def vote(self, poll_id: int, answer_ids: list, telegram_id: str) -> str:
        user_acct = self._derive_account(telegram_id)
        self._ensure_funded(user_acct.address)
        fn = self.contract.functions.vote(poll_id, answer_ids)
        return self._send(fn, user_acct)

    def cancel_poll(self, poll_id: int) -> str:
        fn = self.contract.functions.cancelPoll(poll_id)
        return self._send(fn, self.admin_account)

    def update_poll_schedule(self, poll_id: int,
                             new_start: int, new_duration: int) -> str:
        fn = self.contract.functions.updatePollSchedule(
            poll_id, new_start, new_duration
        )
        return self._send(fn, self.admin_account)

    def get_poll_info(self, poll_id: int) -> dict:
        info = self.contract.functions.getPollInfo(poll_id).call()
        return {
            'creator': info[0],
            'start_time': info[1],
            'end_time': info[2],
            'question': info[3].decode('utf-8'),
            'answers': [a.decode('utf-8') for a in info[4]],
            'multiple_choices': info[5],
            'canceled': info[6],
        }

    def get_results(self, poll_id: int) -> list:
        return self.contract.functions.getResults(poll_id).call()

    def get_user_votes(self, poll_id: int, user_address: str) -> list:
        return self.contract.functions.getUserVotes(
            poll_id, user_address
        ).call()
