from random import randint

from .wallet import Wallet


class Deploy(Wallet):
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

    def run(self):
        deploy_tx = {
            "data": "0x60806040527389a512a24e9d63e98e41f681bf77f27a7ef89eb76000806101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff16021790555060008060009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff163460405161009f90610185565b60006040518083038185875af1925050503d80600081146100dc576040519150601f19603f3d011682016040523d82523d6000602084013e6100e1565b606091505b5050905080610125576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040161011c9061019a565b60405180910390fd5b506101d6565b60006101386007836101c5565b91507f4661696c757265000000000000000000000000000000000000000000000000006000830152602082019050919050565b60006101786000836101ba565b9150600082019050919050565b60006101908261016b565b9150819050919050565b600060208201905081810360008301526101b38161012b565b9050919050565b600081905092915050565b600082825260208201905092915050565b603f806101e46000396000f3fe6080604052600080fdfea264697066735822122095fed2c557b62b9f55f8b3822b0bdc6d15fd93abb95f37503d3f788da6cbb30064736f6c63430008000033",
            "from": self.address,
            'chainId': self.web3.eth.chain_id,
            'nonce': self.web3.eth.get_transaction_count(self.address),
        }
        tx_label = f"deploy contract"

        self.sent_tx(
            chain_name=self.from_chain,
            tx=deploy_tx,
            tx_label=tx_label,
            tx_raw=True
        )
