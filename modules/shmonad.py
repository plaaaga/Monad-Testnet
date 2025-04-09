from random import randint

from .wallet import Wallet


class Shmonad(Wallet):
    def __init__(self, wallet: Wallet):
        super().__init__(
            privatekey=wallet.privatekey,
            encoded_pk=wallet.encoded_pk,
            db=wallet.db,
            browser=wallet.browser,
            recipient=wallet.recipient
        )

        self.from_chain = "monad"
        self.web3 = self.get_web3(self.from_chain)

        self.contract = self.web3.eth.contract(
            address="0x3a98250F98Dd388C211206983453837C8365BDc1",
            abi='[{"type":"function","inputs":[{"name":"assets","type":"uint256","baseType":"uint256","components":null,"arrayLength":null,"arrayChildren":null},{"name":"receiver","type":"address","baseType":"address","components":null,"arrayLength":null,"arrayChildren":null}],"name":"deposit","constant":false,"outputs":[{"name":"","type":"uint256","baseType":"uint256","components":null,"arrayLength":null,"arrayChildren":null}],"stateMutability":"payable","payable":true,"gas":null}, {"type":"function","inputs":[{"name":"account","type":"address","baseType":"address","components":null,"arrayLength":null,"arrayChildren":null}],"name":"balanceOf","constant":true,"outputs":[{"name":"","type":"uint256","baseType":"uint256","components":null,"arrayLength":null,"arrayChildren":null}],"stateMutability":"view","payable":false,"gas":null},{"type":"function","inputs":[{"name":"shares","type":"uint256","baseType":"uint256","components":null,"arrayLength":null,"arrayChildren":null},{"name":"receiver","type":"address","baseType":"address","components":null,"arrayLength":null,"arrayChildren":null},{"name":"owner","type":"address","baseType":"address","components":null,"arrayLength":null,"arrayChildren":null}],"name":"redeem","constant":false,"outputs":[{"name":"","type":"uint256","baseType":"uint256","components":null,"arrayLength":null,"arrayChildren":null}],"stateMutability":"nonpayable","payable":false,"gas":null}]'
        )

    def stake(self, amount: float, value: int):
        stake_tx = self.contract.functions.deposit(value, self.address)
        tx_label = f"shmonad stake {amount} MON"

        self.sent_tx(
            chain_name=self.from_chain,
            tx=stake_tx,
            tx_label=tx_label,
            value=value
        )

    def unstake(self, percent: float):
        staked_value = self.contract.functions.balanceOf(self.address).call()
        if percent == 1:
            unstake_value = staked_value
            unstake_amount = round(unstake_value / 1e18, 5)
        else:
            unstake_amount = round((staked_value * percent) / 1e18, randint(4, 7))
            unstake_value = int(unstake_amount * 1e18)

        stake_tx = self.contract.functions.redeem(unstake_value, self.address, self.address)
        tx_label = f"shmonad unstake {unstake_amount} MON"

        self.sent_tx(
            chain_name=self.from_chain,
            tx=stake_tx,
            tx_label=tx_label
        )
