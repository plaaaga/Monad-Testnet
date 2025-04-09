from random import randint, choice, uniform

from .wallet import Wallet

from .nad_domain import NadDomain
from .buy_meme import BuyMeme
from .shmonad import Shmonad
from .deploy import Deploy
from .apr import Apr

from .utils import sleeping
from .retry import CustomError

import settings


def run_module(module_name: str, **kwargs):
    return MODULES_DATA[module_name]["func"](
        module_name=module_name,
        **kwargs
    )


def run_swap(wallet: Wallet, module_name: str):
    swap_module = MODULES_DATA[module_name]["module"](wallet=wallet)

    swap_amounts = settings.SWAP_AMOUNTS.copy()
    if module_name == "buy_meme":
        token_to_swap = choice(["DAK", "YAKI", "CHOG"])
    else:
        token_to_swap = choice(settings.TOKENS_TO_SWAP[module_name])

    eth_balance = wallet.get_balance(chain_name="monad", human=True)
    if swap_amounts["amounts"] != [0, 0]:
        if eth_balance < swap_amounts["amounts"][0]:
            raise Exception(f"No MON balance ({round(eth_balance, 5)}) for swap ({swap_amounts['amounts'][0]})")
        elif eth_balance < swap_amounts["amounts"][1]:
            swap_amounts["amounts"][1] = eth_balance

        amount_to_swap = round(uniform(*swap_amounts["amounts"]), randint(5, 7))
    else:
        percent = uniform(*swap_amounts["percents"]) / 100
        amount_to_swap = round(eth_balance * percent, randint(5, 7))

    # MON -> token
    to_token_info = wallet.get_token_info("monad", token_to_swap)
    swap_module.swap(
        from_token="MON",
        to_token_info=to_token_info,
        amount=amount_to_swap,
        value=int(amount_to_swap * 1e18),
    )

    if module_name != "buy_meme":
        sleeping(settings.SLEEP_AFTER_TX)
        new_token_info = wallet.get_token_info(chain_name="monad", token_name=token_to_swap)
        percent_back = uniform(*settings.SWAP_AMOUNTS["percent_back"]) / 100

        # token -> MON
        swap_module.swap(
            from_token=token_to_swap,
            to_token="MON",
            amount=round(new_token_info["amount"] * percent_back, randint(5, 7)),
            value=int(new_token_info["value"] * percent_back),
            token_decimals=new_token_info["decimals"]
        )


def run_lending(wallet: Wallet, module_name: str):
    lend_module = MODULES_DATA[module_name]["module"](wallet=wallet)
    lend_amounts = settings.DEPOSIT_AMOUNTS.copy()

    eth_balance = wallet.get_balance(chain_name="monad", human=True)
    if lend_amounts["amounts"] != [0, 0]:
        if eth_balance < lend_amounts["amounts"][0]:
            raise Exception(f"No MON balance ({round(eth_balance, 5)}) to deposit in lending ({lend_amounts['amounts'][0]})")
        elif eth_balance < lend_amounts["amounts"][1]:
            lend_amounts["amounts"][1] = eth_balance

        amount_to_deposit = round(uniform(*lend_amounts["amounts"]), randint(5, 7))
    else:
        percent = uniform(*lend_amounts["percents"]) / 100
        amount_to_deposit = round(eth_balance * percent, randint(5, 7))

    lend_module.deposit(
        amount=amount_to_deposit,
        value=int(amount_to_deposit * 1e18),
    )
    sleeping(settings.SLEEP_AFTER_TX)

    lend_module.withdraw()

def run_stake(wallet: Wallet, module_name: str):
    stake_module = MODULES_DATA[module_name]["module"](wallet=wallet)
    stake_amounts = settings.STAKE_AMOUNTS.copy()

    eth_balance = wallet.get_balance(chain_name="monad", human=True)
    if stake_amounts["amounts"] != [0, 0]:
        if eth_balance < stake_amounts["amounts"][0]:
            raise Exception(f"No MON balance ({round(eth_balance, 5)}) to stake ({stake_amounts['amounts'][0]})")
        elif eth_balance < stake_amounts["amounts"][1]:
            stake_amounts["amounts"][1] = eth_balance

        amount_to_stake = round(uniform(*stake_amounts["amounts"]), randint(5, 7))
    else:
        percent = uniform(*stake_amounts["percents"]) / 100
        amount_to_stake = round(eth_balance * percent, randint(5, 7))

    stake_module.stake(
        amount=amount_to_stake,
        value=int(amount_to_stake * 1e18),
    )
    sleeping(settings.SLEEP_AFTER_TX)

    stake_module.unstake(percent=uniform(*stake_amounts["percent_back"]) / 100)

def run_custom(wallet: Wallet, module_name: str):
    MODULES_DATA[module_name]["module"](wallet=wallet).run()


MODULES_DATA = {
    "buy_meme": {"func": run_swap, "module": BuyMeme},
    "shmonad": {"func": run_stake, "module": Shmonad},
    "apr": {"func": run_stake, "module": Apr},
    "deploy": {"func": run_custom, "module": Deploy},
    "nad_domain": {"func": run_custom, "module": NadDomain},
}
