from pprint import pformat
from .logger import logger


class CozaException(Exception):
    def __init__(self, msg, **kwargs):
        self.msg = msg
        logger.error(msg)
        super().__init__(**kwargs)

    def __str__(self):
        return self.msg
    
    
class CozaNotAuthenticatedException(CozaException):
    default_msg = 'User is not authenticated'
    
    def __init__(self, msg=None, **kwargs):
        msg = msg or self.default_msg
        super().__init__(msg, **kwargs)


class NoEnvKeyError(CozaException):
    default_msg = 'There is no environment variable'

    def __init__(self, env, **kwargs):
        msg = f'{self.default_msg}: {env}'
        super().__init__(msg, **kwargs)


class CozaRequestException(CozaException):
    def __init__(self, req, resp, **kwargs):
        self.req = req
        self.resp = resp
        msg = f'Coza API Error\n{self.dump_req()}\n{self.dump_resp()}'
        super().__init__(msg, **kwargs)

    def dump_req(self):
        req = self.req.__dict__
        return f"============request============\n"\
               f"{req['method']} {req['url']}\n" \
               f"headers: {pformat(req['headers'])}\n" \
               f"body: {req['body']}"
               
    def dump_resp(self):
        resp = self.resp.__dict__
        return f"===========response============\n"\
               f"{resp['status_code']} {resp['url']}\n" \
               f"headers: {pformat(resp['headers'])}\n" \
               f"content: {resp['_content'].decode()}"

class CozaCurrencyException(CozaException):
    default_msg = 'This currency not support'

    def __init__(self, currency, **kwargs):
        msg = f'{self.default_msg}: {currency}'
        super().__init__(msg, **kwargs)

class CozaExchangeException(CozaException):
    default_msg = 'This exchange not support'

    def __init__(self, exchange, **kwargs):
        msg = f'{self.default_msg}: {exchange}'
        super().__init__(msg, **kwargs)

class InputValueValidException(CozaException):
    default_msg = 'Invalid input value.'
    def __init__(self, c_func, param_, value_, **kwargs):
        msg = f'{self.default_msg} Call Function : {c_func}, {param_} : {value_} {type(value_)}'
        super().__init__(msg, **kwargs)

