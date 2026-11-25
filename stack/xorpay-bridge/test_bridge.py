"""转接服务单元测试（只用标准库）：python3 -I stack/xorpay-bridge/test_bridge.py -v"""
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge  # noqa: E402

AID, SECRET = "test-aid", "test-secret-0123456789"


def serve(handler_cls):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def post(url, params):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(params).encode(), method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=10) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


class FakeXorPay(BaseHTTPRequestHandler):
    calls = []
    query_status = {}    # aoid → 查单返回的状态；不在表里 = "new"（没付款）
    create_status = None  # 设了就让下单返回这个错误状态

    def _send_json(self, body, code=200):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        p = dict(urllib.parse.parse_qsl(self.rfile.read(int(self.headers["Content-Length"])).decode()))
        FakeXorPay.calls.append((self.path, p))
        if FakeXorPay.create_status:
            return self._send_json({"status": FakeXorPay.create_status, "info": "ACQ.ACCESS_FORBIDDEN"})
        ok = p["sign"] == bridge.xorpay_pay_sign(p["name"], p["pay_type"], p["price"], p["order_id"], p["notify_url"], SECRET)
        self._send_json({"status": "ok", "aoid": "AOID-" + p["order_id"], "expires_in": 600,
                         "info": {"qr": "https://qr.alipay.com/test" + p["order_id"]}} if ok else {"status": "sign_error"})

    def do_GET(self):
        aoid = urllib.parse.unquote(self.path.rsplit("/", 1)[-1])
        status = FakeXorPay.query_status.get(aoid, "new")
        if status == "BROKEN":
            return self._send_json({"error": "boom"}, code=500)
        self._send_json({"status": status})

    def log_message(self, *a):
        pass


class FakeDujiao(BaseHTTPRequestHandler):
    received = []
    reply = "success"

    def do_POST(self):
        p = dict(urllib.parse.parse_qsl(self.rfile.read(int(self.headers["Content-Length"])).decode(), keep_blank_values=True))
        FakeDujiao.received.append(p)
        valid = p.get("sign") == bridge.epay_sign(p, SECRET) and p.get("pid") == AID
        data = (FakeDujiao.reply if valid else "fail").encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


class SignTests(unittest.TestCase):
    def test_epay_sign_rule(self):
        p = {"b": "2", "a": "1", "empty": "", "sign": "x", "sign_type": "MD5"}
        self.assertEqual(bridge.epay_sign(p, "KEY"), bridge.md5("a=1&b=2KEY"))

    def test_money2(self):
        self.assertEqual(bridge.money2("10"), "10.00")
        self.assertEqual(bridge.money2("0.5"), "0.50")
        self.assertIsNone(bridge.money2("0"))
        self.assertIsNone(bridge.money2("abc"))
        self.assertIsNone(bridge.money2("NaN"))


class FlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.xor, xor_url = serve(FakeXorPay)
        cls.dj, cls.dj_url = serve(FakeDujiao)
        cls.tmp = tempfile.TemporaryDirectory()
        cfg = bridge.Config(aid=AID, secret=SECRET, public_base_url="https://shop.example", api_base=xor_url,
                            expire=600, fallback_notify_url=cls.dj_url + "/fallback", port=0,
                            db_path=os.path.join(cls.tmp.name, "b.db"))
        cls.srv = bridge.make_server(cfg, host="127.0.0.1")
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        for s in (cls.srv, cls.xor, cls.dj):
            s.shutdown()
        cls.tmp.cleanup()

    def setUp(self):
        FakeDujiao.received.clear()
        FakeDujiao.reply = "success"
        FakeXorPay.create_status = None

    def create(self, order, money="10.00", key=SECRET, pid=AID, typ="alipay"):
        p = {"pid": pid, "type": typ, "out_trade_no": order, "notify_url": self.dj_url + "/cb",
             "return_url": "https://shop.example/pay", "name": "测试商品", "money": money, "clientip": "1.2.3.4", "device": "pc"}
        p["sign"] = bridge.epay_sign(p, key)
        p["sign_type"] = "MD5"
        code, body = post(self.url + "/mapi.php", p)
        self.assertEqual(code, 200)
        return json.loads(body)

    def notify(self, order, price="10.00", secret=SECRET, paid=True):
        aoid, t = "AOID-" + order, "2026-11-24 12:00:00"
        if paid:
            FakeXorPay.query_status.setdefault(aoid, "payed")   # XorPay 查单：已付款
        return post(self.url + "/xorpay/notify", {"aoid": aoid, "order_id": order, "pay_price": price, "pay_time": t,
                                                   "sign": bridge.xorpay_notify_sign(aoid, order, price, t, secret)})

    def test_notify_rejected_when_xorpay_says_unpaid(self):
        self.create("DJP007")
        self.assertEqual(self.notify("DJP007", paid=False), (400, "not paid"))   # 签名对，但查单说没付款
        self.assertEqual(FakeDujiao.received, [])

    def test_query_failure_returns_502_then_retry_succeeds(self):
        self.create("DJP008")
        FakeXorPay.query_status["AOID-DJP008"] = "BROKEN"
        self.assertEqual(self.notify("DJP008"), (502, "query failed"))
        self.assertEqual(FakeDujiao.received, [])
        FakeXorPay.query_status["AOID-DJP008"] = "payed"
        self.assertEqual(self.notify("DJP008"), (200, "ok"))

    def test_fee_error_counts_as_paid(self):
        self.create("DJP009")
        FakeXorPay.query_status["AOID-DJP009"] = "fee_error"
        self.assertEqual(self.notify("DJP009"), (200, "ok"))
        self.assertEqual(FakeDujiao.received[-1]["out_trade_no"], "DJP009")

    def test_create_error_has_hint(self):
        FakeXorPay.create_status = "alipay_api_error"
        r = self.create("DJP010")
        self.assertEqual(r["code"], -1)
        self.assertIn("支付宝未签约", r["msg"])

    def test_full_flow_and_duplicate(self):
        r = self.create("DJP001")
        self.assertEqual(r["code"], 1)
        self.assertTrue(r["qrcode"].startswith("https://qr.alipay.com/"))
        self.assertEqual(r["payurl"], r["qrcode"])
        path, sent = FakeXorPay.calls[-1]
        self.assertEqual(path, f"/api/pay/{AID}")
        self.assertEqual(sent["notify_url"], "https://shop.example/xorpay/notify")
        self.assertEqual(sent["pay_type"], "alipay")

        self.assertEqual(self.notify("DJP001"), (200, "ok"))
        cb = FakeDujiao.received[-1]
        self.assertEqual(cb["trade_status"], "TRADE_SUCCESS")
        self.assertEqual(cb["out_trade_no"], "DJP001")
        self.assertEqual(cb["money"], "10.00")
        self.assertEqual(cb["sign"], bridge.epay_sign(cb, SECRET))

        n = len(FakeDujiao.received)
        self.assertEqual(self.notify("DJP001"), (200, "ok"))      # 重复通知：不再转发
        self.assertEqual(len(FakeDujiao.received), n)

    def test_reuse_qr_for_same_order(self):
        first = self.create("DJP002")
        calls = len(FakeXorPay.calls)
        second = self.create("DJP002")
        self.assertEqual(first["qrcode"], second["qrcode"])
        self.assertEqual(len(FakeXorPay.calls), calls)

    def test_rejects_bad_dujiao_sign_and_pid(self):
        self.assertEqual(self.create("DJP003", key="wrong")["code"], -1)
        self.assertEqual(self.create("DJP003", pid="other")["code"], -1)

    def test_rejects_unsupported_type_and_bad_money(self):
        self.assertEqual(self.create("DJP004", typ="qqpay")["code"], -1)
        self.assertEqual(self.create("DJP004", money="0")["code"], -1)

    def test_notify_bad_sign_and_amount_mismatch(self):
        self.create("DJP005")
        self.assertEqual(self.notify("DJP005", secret="wrong")[0], 400)
        self.assertEqual(self.notify("DJP005", price="9.99"), (400, "amount mismatch"))
        self.assertEqual(FakeDujiao.received, [])

    def test_dujiao_failure_returns_502_then_retry_succeeds(self):
        self.create("DJP006")
        FakeDujiao.reply = "fail"
        self.assertEqual(self.notify("DJP006"), (502, "forward failed"))
        FakeDujiao.reply = "success"
        self.assertEqual(self.notify("DJP006"), (200, "ok"))

    def test_unknown_order_uses_fallback(self):
        self.assertEqual(self.notify("DJP-UNKNOWN", price="5"), (200, "ok"))
        cb = FakeDujiao.received[-1]
        self.assertEqual(cb["out_trade_no"], "DJP-UNKNOWN")
        self.assertEqual(cb["money"], "5.00")


if __name__ == "__main__":
    unittest.main()
