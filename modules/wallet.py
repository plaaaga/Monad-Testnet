from eth_account.messages import (
    encode_defunct,
    encode_typed_data,
    _hash_eip191_message
)
from web3.middleware import geth_poa_middleware
from random import choice, uniform, randint
from typing import Union, Optional
from web3.types import Hash32
from time import sleep, time
from web3 import Web3

from modules.utils import logger, sleeping
from modules.database import DataBase
import modules.config as config
import settings

from requests.exceptions import HTTPError
from web3.exceptions import ContractLogicError, BadFunctionCallOutput


class Wallet:
    def __init__(
            self,
            privatekey: str,
            encoded_pk: str,
            db: DataBase,
            browser=None,
            recipient: str = None,
    ):
        self.privatekey = privatekey
        self.encoded_pk = encoded_pk

        self.account = Web3().eth.account.from_key(privatekey)
        self.address = self.account.address
        self.recipient = Web3().to_checksum_address(recipient) if recipient else None
        self.browser = browser
        self.db = db


    def get_web3(self, chain_name: str):
        web3 = Web3(Web3.HTTPProvider(settings.RPCS[chain_name]))
        web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        return web3


    def wait_for_gwei(self):
        for chain_data in [
            {'chain_name': 'ethereum', 'max_gwei': settings.ETH_MAX_GWEI},
        ]:
            first_check = True
            while True:
                try:
                    new_gwei = round(self.get_web3(chain_name=chain_data['chain_name']).eth.gas_price / 10 ** 9, 2)
                    if new_gwei < chain_data["max_gwei"]:
                        if not first_check: logger.debug(f'[•] Web3 | New {chain_data["chain_name"].title()} GWEI is {new_gwei}')
                        break
                    sleep(5)
                    if first_check:
                        first_check = False
                        logger.debug(f'[•] Web3 | Waiting for GWEI in {chain_data["chain_name"].title()} at least {chain_data["max_gwei"]}. Now it is {new_gwei}')
                except Exception as err:
                    logger.warning(f'[•] Web3 | {chain_data["chain_name"].title()} gwei waiting error: {err}')
                    sleeping(10)


    def get_gas(self, chain_name, increasing_gwei: float = 0):
        web3 = self.get_web3(chain_name=chain_name)
        max_priority = int(web3.eth.max_priority_fee)
        last_block = web3.eth.get_block('latest')
        base_fee = int(max(last_block['baseFeePerGas'], web3.eth.gas_price) * (settings.GWEI_MULTIPLIER + increasing_gwei))
        block_filled = last_block['gasUsed'] / last_block['gasLimit'] * 100
        if block_filled > 50: base_fee = int(base_fee * 1.127)

        max_fee = int(base_fee + max_priority)
        return {'maxPriorityFeePerGas': max_priority, 'maxFeePerGas': max_fee}


    def sent_tx(self, chain_name: str, tx, tx_label, tx_raw=False, value=0, increasing_gwei: float = 0):
        try:
            web3 = self.get_web3(chain_name=chain_name)
            if not tx_raw:
                tx_completed = tx.build_transaction({
                    'from': self.address,
                    'chainId': web3.eth.chain_id,
                    'nonce': web3.eth.get_transaction_count(self.address),
                    'value': value,
                    **self.get_gas(chain_name=chain_name, increasing_gwei=increasing_gwei),
                })
            else:
                tx_completed = {
                    **tx,
                    **self.get_gas(chain_name=chain_name, increasing_gwei=increasing_gwei),
                }
                tx_completed["gas"] = web3.eth.estimate_gas(tx_completed)

            signed_tx = web3.eth.account.sign_transaction(tx_completed, self.privatekey)

            raw_tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash = web3.to_hex(raw_tx_hash)
            return self.wait_for_tx(
                chain_name=chain_name,
                tx_hash=tx_hash,
                tx_label=tx_label
            )

        except Exception as err:
            if 'already known' in str(err):
                try: raw_tx_hash
                except: raw_tx_hash = ''
                logger.warning(f'{tx_label} | Couldnt get tx hash, thinking tx is success ({raw_tx_hash})')
                sleeping(15)
                return tx_hash

            elif (
                    "replacement transaction underpriced" in str(err) or
                    "not in the chain after" in str(err) or
                    "max fee per gas less than block base fee" in str(err)
                ):
                new_multiplier = round((increasing_gwei + 0.05 + settings.GWEI_MULTIPLIER - 1) * 100)
                logger.warning(f'[-] Web3 | {tx_label} | couldnt send tx, increasing gwei to {new_multiplier}%')
                return self.sent_tx(
                    chain_name=chain_name,
                    tx=tx,
                    tx_label=tx_label,
                    tx_raw=tx_raw,
                    value=value,
                    increasing_gwei=increasing_gwei+0.05
                )

            try: encoded_tx = f'\nencoded tx: {tx_completed._encode_transaction_data()}'
            except: encoded_tx = ''
            raise ValueError(f'tx failed error: {err}{encoded_tx}')


    def wait_for_tx(self, chain_name: str, tx_hash: str, tx_label: str):
        tx_link = f'{config.CHAINS_DATA[chain_name]["explorer"]}{tx_hash}'
        logger.debug(f'[•] Web3 | {tx_label} tx sent: {tx_link}')

        web3 = self.get_web3(chain_name)
        while True:
            try:
                status = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=int(settings.TO_WAIT_TX * 60)).status
                break
            except HTTPError as err:
                logger.error(f'[-] Web3 | Coudlnt get TX, probably you need to change RPC: {err}')
                sleeping(5)

        if status == 1:
            logger.info(f'[+] Web3 | {tx_label} tx confirmed\n')
            self.db.append_report(privatekey=self.encoded_pk, text=tx_label, success=True)
            return tx_hash
        else:
            self.db.append_report(
                privatekey=self.encoded_pk,
                text=f'{tx_label} | tx is failed | <a href="{tx_link}">link 👈</a>', success=False
            )
            raise ValueError(f'tx failed: {tx_link}')

    def approve(self, chain_name: str, token_name: str, spender: str, amount: float = None, value: int = None):
        web3 = self.get_web3(chain_name)
        contract = web3.eth.contract(
            address=config.TOKEN_ADDRESSES[token_name],
            abi='[{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"}]',
        )

        if amount:
            value = int(amount * 1e18)
        elif value:
            amount = round(value / 1e18, 4)

        if contract.functions.allowance(
            self.address,
            spender,
        ).call() < value:
            module_str = f"approve {amount} ${token_name}"
            contract_tx = contract.functions.approve(
                spender,
                value
            )
            self.sent_tx(
                chain_name=chain_name,
                tx=contract_tx,
                tx_label=module_str
            )
            sleeping(settings.SLEEP_AFTER_TX)
            return True

    def get_balance(self, chain_name: str, token_name=False, token_address=False, human=False, tokenId=None):
        web3 = self.get_web3(chain_name=chain_name)
        if token_name: token_address = config.TOKEN_ADDRESSES[token_name]
        if token_address:
            contract = web3.eth.contract(
                address=web3.to_checksum_address(token_address),
                abi='[{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"uint256","name":"","type":"uint256"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]'
            )

        while True:
            try:
                if token_address:
                    if tokenId is not None:
                        if type(tokenId) != list:
                            params = [self.address, tokenId]
                        else:
                            param = tokenId[0]
                            if param is None:
                                params = [self.address]
                            else:
                                params = [self.address, param]
                    else:
                        params = [self.address]
                    balance = contract.functions.balanceOf(*params).call()
                else: balance = web3.eth.get_balance(self.address)

                if not human: return balance

                decimals = contract.functions.decimals().call() if token_address else 18
                return balance / 10 ** decimals

            except ContractLogicError:
                if type(tokenId) == list and len(tokenId) != 0:
                    tokenId.pop(0)

                elif tokenId is not None:
                    tokenId = None
                    continue

                if (
                        type(tokenId) == list and len(tokenId) == 0
                        or
                        type(tokenId) is not list
                ):
                    raise

            except BadFunctionCallOutput:
                logger.warning(f'[-] Web3 | Bad address to get balance: {token_address}')
                return None

            except Exception as err:
                logger.warning(f'[•] Web3 | Get {token_address} balance error ({tokenId}): {err}')
                sleep(5)

    def get_token_info(self, chain_name: str, token_name=False, token_address=False):
        web3 = self.get_web3(chain_name=chain_name)
        if token_name: token_address = config.TOKEN_ADDRESSES[token_name]
        if token_address:
            token_address = web3.to_checksum_address(token_address)
            contract = web3.eth.contract(
                address=token_address,
                abi='[{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"uint256","name":"","type":"uint256"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"}]'
            )

        while True:
            try:
                if token_address:
                    balance = contract.functions.balanceOf(self.address).call()
                    decimals = contract.functions.decimals().call()
                    symbol = contract.functions.symbol().call()
                else:
                    balance = web3.eth.get_balance(self.address)
                    decimals = 18
                    symbol = "MON"
                    token_address = "0x0000000000000000000000000000000000000000"

                return {
                    "value": balance,
                    "amount": balance / 10 ** decimals,
                    "decimals": decimals,
                    "symbol": symbol,
                    "address": token_address,
                }

            except BadFunctionCallOutput:
                logger.warning(f'[-] Web3 | Bad address to get balance: {token_address}')
                return None

            except Exception as err:
                logger.warning(f'[•] Web3 | Get {token_address} balance error: {err}')
                sleep(5)


    def wait_balance(self,
                     chain_name: str,
                     needed_balance: Union[int, float],
                     only_more: bool = False,
                     token_name: Optional[str] = False,
                     token_address: Optional[str] = False,
                     human: bool = True,
                     timeout: int = 0
    ):
        " needed_balance: human digit "
        if token_name:
            token_address = config.TOKEN_ADDRESSES[token_name]

        if token_address:
            contract = self.get_web3(chain_name=chain_name).eth.contract(address=Web3().to_checksum_address(token_address),
                                         abi='[{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"}]')
            token_name = contract.functions.name().call()

        else:
            token_name = 'ETH'

        if only_more: logger.debug(f'[•] Web3 | Waiting for balance more than {round(needed_balance, 6)} {token_name} in {chain_name.upper()}')
        else: logger.debug(f'[•] Web3 | Waiting for {round(needed_balance, 6)} {token_name} balance in {chain_name.upper()}')
        start_time = time()

        while True:
            try:
                new_balance = self.get_balance(chain_name=chain_name, human=human, token_address=token_address)

                if only_more: status = new_balance > needed_balance
                else: status = new_balance >= needed_balance
                if status:
                    logger.debug(f'[•] Web3 | New balance: {round(new_balance, 6)} {token_name}\n')
                    return new_balance
                if timeout and time() - start_time > timeout:
                    logger.error(f'[-] Web3 | No token found in {timeout} seconds')
                    return 0
                sleep(5)
            except Exception as err:
                logger.warning(f'[•] Web3 | Wait balance error: {err}')
                sleep(10)


    def sign_message(
            self,
            text: str = None,
            typed_data: dict = None,
            hash: bool = False
    ):
        if text:
            message = encode_defunct(text=text)
        elif typed_data:
            message = encode_typed_data(full_message=typed_data)
            if hash:
                message = encode_defunct(hexstr=_hash_eip191_message(message).hex())

        signed_message = self.account.sign_message(message)
        signature = signed_message.signature.hex()
        if not signature.startswith('0x'): signature = '0x' + signature
        return signature
