from loguru import logger
from faker import Faker

from .wallet import Wallet


class NadDomain(Wallet):
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

        self.domains_contract = self.web3.eth.contract(
            address="0x3019BF1dfB84E5b46Ca9D0eEC37dE08a59A41308",
            abi='[{"inputs":[{"internalType":"string","name":"name","type":"string"}],"name":"isNameAvailable","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"uint256","name":"index","type":"uint256"}],"name":"tokenOfOwnerByIndex","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]'
        )
        self.register_contract = self.web3.eth.contract(
            address="0x758D80767a751fc1634f579D76e1CcaAb3485c9c",
            abi='[{"inputs":[{"components":[{"internalType":"string","name":"name","type":"string"},{"internalType":"address","name":"nameOwner","type":"address"},{"internalType":"bool","name":"setAsPrimaryName","type":"bool"},{"internalType":"address","name":"referrer","type":"address"},{"internalType":"bytes32","name":"discountKey","type":"bytes32"},{"internalType":"bytes","name":"discountClaimProof","type":"bytes"},{"internalType":"uint256","name":"nonce","type":"uint256"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"internalType":"structNNSRegistrarController.RegisterData","name":"params","type":"tuple"},{"internalType":"bytes","name":"signature","type":"bytes"}],"name":"registerWithSignature","outputs":[],"stateMutability":"payable","type":"function"}]'
        )

        self.mint_price = 0.02

    def run(self):
        try:
            self.domains_contract.functions.tokenOfOwnerByIndex(self.address, 0).call()
            logger.warning(f'[•] Monad | Nad Domain already minted!')
            self.db.append_report(
                privatekey=self.encoded_pk,
                text="mint nad domain: domain already minted",
                success=False
            )
            return True
        except:
            pass

        while True:
            username = Faker().user_name()
            if len(username) >= 5 and self.domains_contract.functions.isNameAvailable(username).call(): break

        domain_data = self.browser.register_domain(username)
        domain_tx = self.register_contract.functions.registerWithSignature(
            [
                username,
                self.address,
                True,
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000000000000000000000000000",
                int(domain_data["nonce"]),
                int(domain_data["deadline"]),
            ],
            domain_data["signature"]
        )
        tx_label = f'nad domain mint "{username}" for {self.mint_price} MOD'

        self.sent_tx(
            chain_name=self.from_chain,
            tx=domain_tx,
            tx_label=tx_label,
            value=int(self.mint_price * 1e18)
        )
