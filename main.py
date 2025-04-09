from modules.utils import sleeping, logger, sleep, choose_mode
from modules.retry import DataBaseError
from modules import *


def run_modules():
    while True:
        print('')
        try:
            module_data = db.get_random_module()

            if module_data == 'No more accounts left':
                logger.success(f'All accounts done.')
                return 'Ended'

            browser = Browser(db=db, encoded_pk=module_data["encoded_privatekey"], proxy=module_data["proxy"])
            wallet = Wallet(
                privatekey=module_data["privatekey"],
                encoded_pk=module_data["encoded_privatekey"],
                recipient=module_data["recipient"],
                browser=browser,
                db=db,
            )
            browser.address = wallet.address
            logger.info(f'[•] Web3 | {wallet.address} | Starting {module_data["module_info"]["module_name"].replace("_", " ").title()}')

            run_module(
                wallet=wallet,
                module_name=module_data["module_info"]["module_name"]
            )
            module_data["module_info"]["status"] = True

        except Exception as err:
            logger.error(f'[-] Web3 | Account error: {err}')
            db.append_report(privatekey=wallet.encoded_pk, text=str(err), success=False)

        finally:
            if type(module_data) == dict:
                db.remove_module(module_data=module_data)

                if module_data['last']:
                    reports = db.get_account_reports(privatekey=wallet.encoded_pk)
                    TgReport().send_log(logs=reports)

                # if module_data["module_info"]["status"] is True: sleeping(settings.SLEEP_AFTER_ACC)
                # else: sleeping(10)


if __name__ == '__main__':
    try:
        db = DataBase()

        while True:
            mode = choose_mode()

            match mode:
                case None: break

                case 'Delete and create new':
                    db.create_modules()

                case 1:
                    if run_modules() == 'Ended': break
                    print('')

        sleep(0.1)
        input('\n > Exit\n')

    except DataBaseError as e:
        logger.error(f'[-] Database | {e}')

    except KeyboardInterrupt:
        pass

    finally:
        logger.info('[•] Soft | Closed')
