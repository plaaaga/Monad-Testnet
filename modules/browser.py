from tls_client import Session
from requests import get, post
from time import sleep
from uuid import uuid4
from json import loads

from modules.retry import retry, have_json
from modules.utils import logger, sleeping
from modules.database import DataBase
import settings


class Browser:
    def __init__(self, db: DataBase, encoded_pk: str, proxy: str):
        self.max_retries = 5
        self.db = db
        self.encoded_pk = encoded_pk
        if proxy == "mobile":
            self.proxy = settings.PROXY
        else:
            self.proxy = "http://" + proxy.removeprefix("https://").removeprefix("http://")
            logger.debug(f'[•] Soft | Got proxy {self.proxy}')

        if self.proxy not in ['http://log:pass@ip:port', '', None]:
            if proxy == "mobile": self.change_ip()
        else:
            logger.warning(f'[-] Soft | You dont use proxies!')

        self.session = self.get_new_session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
        })
        self.address = None


    def get_new_session(self):
        session = Session(
            client_identifier="safari_16_0",
            random_tls_extension_order=True
        )

        if self.proxy not in ['http://log:pass@ip:port', '', None]:
            session.proxies.update({'http': self.proxy, 'https': self.proxy})

        return session


    @have_json
    def send_request(self, **kwargs):
        if kwargs.get("method"): kwargs["method"] = kwargs["method"].upper()
        return self.session.execute_request(**kwargs)


    def change_ip(self):
        if settings.CHANGE_IP_LINK not in ['https://changeip.mobileproxy.space/?proxy_key=...&format=json', '']:
            print('')
            while True:
                try:
                    r = get(settings.CHANGE_IP_LINK)
                    if 'mobileproxy' in settings.CHANGE_IP_LINK and r.json().get('status') == 'OK':
                        logger.debug(f'[+] Proxy | Successfully changed ip: {r.json()["new_ip"]}')
                        return True
                    elif not 'mobileproxy' in settings.CHANGE_IP_LINK and r.status_code == 200:
                        logger.debug(f'[+] Proxy | Successfully changed ip: {r.text}')
                        return True
                    logger.error(f'[-] Proxy | Change IP error: {r.text} | {r.status_code}')
                    sleep(10)

                except Exception as err:
                    logger.error(f'[-] Browser | Cannot get proxy: {err}')


    @retry(source="Browser", module_str="Get MEME swap tx", exceptions=Exception)
    def get_meme_swap_tx(
            self,
            output_address: str,
            output_symbol: str,
            output_decimals: int,
            amount: float
    ):

        api_url = f"https://uniswap.api.dial.to/swap/confirm?"
        params = {
            "chain": "monad-testnet",
            "inputCurrency": "native",
            "outputCurrency": output_address,
            "inputSymbol": "MON",
            "outputSymbol": output_symbol,
            "inputDecimals": 18,
            "outputDecimals": output_decimals,
            "amount": amount,
            "_brf": str(uuid4()),
            "_bin": str(uuid4()),
        }
        api_url += "&".join([f"{k}={v}" for k, v in params.items()])
        r = self.send_request(
            method="POST",
            url=f"https://api.dial.to/v1/blink",
            json={"account": self.address, "type": "transaction"},
            params={"apiUrl": api_url}
        )
        if r.json().get('transaction'):
            return loads(r.json()["transaction"])
        raise Exception(f'Unexpected response: {r.json()}')


    @retry(source="Browser", module_str="Register Nad Domain", exceptions=Exception)
    def register_domain(self, domain: str):
        params = {
            "name": domain,
            "nameOwner": self.address,
            "setAsPrimaryName": "true",
            "referrer": "0x0000000000000000000000000000000000000000",
            "discountKey": "0x0000000000000000000000000000000000000000000000000000000000000000",
            "discountClaimProof": "0x0000000000000000000000000000000000000000000000000000000000000000",
            "chainId": "10143",
        }
        r = self.send_request(
            method="GET",
            url="https://api.nad.domains/register/signature",
            params=params,
            headers={
                "Origin": "https://app.nad.domains",
                "Referer": "https://app.nad.domains/",
            }
        )
        if r.json().get('success') is True:
            return r.json()
        raise Exception(f'Unexpected response: {r.json()}')
