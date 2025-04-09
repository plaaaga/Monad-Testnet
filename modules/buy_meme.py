from .wallet import Wallet


class BuyMeme(Wallet):
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

    def swap(
            self,
            from_token: str,
            to_token_info: dict,
            amount: float,
            value: int,
    ):
        swap_data = self.browser.get_meme_swap_tx(
            output_address=to_token_info["address"],
            output_symbol=to_token_info["symbol"],
            output_decimals=to_token_info["decimals"],
            amount=amount,
        )
        swap_tx = {
            "from": self.address,
            "to": self.web3.to_checksum_address(swap_data["to"]),
            "data": swap_data["data"],
            "value": int(swap_data["value"], 16),
            'chainId': self.web3.eth.chain_id,
            'nonce': self.web3.eth.get_transaction_count(self.address),
        }
        tx_label = f"buy meme {amount} {from_token} -> {to_token_info['symbol']}"

        self.sent_tx(
            chain_name=self.from_chain,
            tx=swap_tx,
            tx_label=tx_label,
            tx_raw=True,
        )
