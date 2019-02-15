from pprint import pformat


class ExchangeAPIException(Exception):
  def __init__(self, exchange, req, resp, status_code, message):
    self.exchange = exchange
    self.req = req
    self.resp = resp
    self.status_code = status_code
    self.detail = message

  def __str__(self):
    return  f'{self.exchange.upper()} API Error: {self.detail}\n' \
        f'==========requests==========\n' \
        f'{self.dump_req()}\n' \
        f'==========response==========\n' \
        f'{self.dump_resp()}'

  def dump_req(self):
    req = self.req.__dict__
    return  f"{req['method']} {req['url']}\n" + \
        f"headers: {pformat(req['headers'])}\n" + \
        f"body: {req['body'].decode()}" if req['body'] else ""

  def dump_resp(self):
    resp = self.resp.__dict__
    return  f"{resp['status_code']} {resp['url']}\n" \
        f"headers: {pformat(resp['headers'])}\n" \
        f"content: {resp['_content'].decode()}"
