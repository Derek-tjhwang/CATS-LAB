import imp
import coza.errors
from coza.api import ExchangeApi


def load_functions(code):
    try:
        alg = imp.new_module('myalgo')
        exec(code, alg.__dict__)
        initialize = getattr(alg, 'initialize')
        run_strategy = getattr(alg, 'run_strategy')
        make_orders = getattr(alg, 'make_orders')

        return (initialize, run_strategy, make_orders)
    except AttributeError as e:
        raise coza.errors.CozaException(str(e))
    except:
        raise coza.errors.CozaException(f'Failed to load algorithm module')


def validation_exchange_currency(exchange, currency):
    exchange = exchange.lower()
    currency = currency.upper()
    exchange_info = ExchangeApi.get_exchange_info()

    if exchange in exchange_info.keys():
        if currency in exchange_info[exchange]:
            return True
        raise coza.errors.CozaCurrencyException(currency)
    raise coza.errors.CozaExchangeException(exchange)
