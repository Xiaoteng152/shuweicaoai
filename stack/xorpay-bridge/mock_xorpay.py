#!/usr/bin/env python3
"""本地测试用的假 XorPay（不要在线上运行）。只用标准库。

  MOCK_SECRET=<和 .env 里 XORPAY_APP_SECRET 相同> python3 mock_xorpay.py   # 默认只监听 127.0.0.1:9999

  POST /api/pay/<aid>             模拟下单：校验签名，返回假的支付宝二维码
  POST /mock/pay?order_id=X       模拟买家付款：按 XorPay 格式签名后回调下单时的 notify_url
       &price=Y（可选，模拟金额不符）  返回转接服务的响应
本地测试时 .env 里设 XORPAY_API_BASE=http://host.docker.internal:9999，转接服务就会把下单请求发到这里。
"""
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SECRET = os.environ.get("MOCK_SECRET", "")
PORT = int(os.environ.get("MOCK_PORT", "9999"))
HOST = os.environ.get("MOCK_HOST", "127.0.0.1")
ORDERS = {}


def md5(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest().lower()


class Handler(BaseHTTPRequestHandler):
    def _params(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode() if length else ""
        params = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(self.path).query))
        params.update(urllib.parse.parse_qsl(body, keep_blank_values=True))
        return params

    def _json(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        path = urllib.parse.urlsplit(self.path).path
        p = self._params()
        if path.startswith("/api/pay/"):
            want = md5(p.get("name", "") + p.get("pay_type", "") + p.get("price", "") + p.get("order_id", "") + p.get("notify_url", "") + SECRET)
            if p.get("sign") != want:
                return self._json(200, {"status": "sign_error"})
            old = ORDERS.get(p["order_id"])
            if old and old["price"] != p["price"]:
                return self._json(200, {"status": "order_exist"})
            aoid = old["aoid"] if old else uuid.uuid4().hex
            ORDERS[p["order_id"]] = {"aoid": aoid, "price": p["price"], "notify_url": p["notify_url"]}
            print(f"[mock] 下单 order_id={p['order_id']} price={p['price']} pay_type={p['pay_type']}", flush=True)
            return self._json(200, {"status": "ok", "aoid": aoid, "expires_in": int(p.get("expire") or 7200),
                                    "info": {"qr": f"https://qr.alipay.com/mock{aoid[:12]}"}})
        if path == "/mock/pay":
            order = ORDERS.get(p.get("order_id", ""))
            if not order:
                return self._json(404, {"error": "order not found"})
            pay_price = p.get("price") or order["price"]
            pay_time = time.strftime("%Y-%m-%d %H:%M:%S")
            form = {"aoid": order["aoid"], "order_id": p["order_id"], "pay_price": pay_price, "pay_time": pay_time,
                    "more": "", "detail": "{}", "sign": md5(order["aoid"] + p["order_id"] + pay_price + pay_time + SECRET)}
            req = urllib.request.Request(order["notify_url"], data=urllib.parse.urlencode(form).encode(), method="POST",
                                         headers={"Content-Type": "application/x-www-form-urlencoded"})
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            try:
                with opener.open(req, timeout=20) as r:
                    result = {"notify_status": r.status, "notify_body": r.read().decode()}
            except urllib.error.HTTPError as e:
                result = {"notify_status": e.code, "notify_body": e.read().decode()}
            print(f"[mock] 回调 order_id={p['order_id']} pay_price={pay_price} → {result}", flush=True)
            return self._json(200, result)
        return self._json(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    if not SECRET:
        raise SystemExit("先设置 MOCK_SECRET（和 XORPAY_APP_SECRET 相同）")
    print(f"[mock] XorPay 假服务监听 {HOST}:{PORT}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
