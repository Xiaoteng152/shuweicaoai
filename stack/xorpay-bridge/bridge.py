#!/usr/bin/env python3
"""XorPay ⇄ 易支付（v1）转接服务：让 Dujiao-Next 自带的「易支付」渠道直接用 XorPay 收款，不改官方代码。

  买家下单 → Dujiao ──POST /mapi.php（易支付 v1，MD5 签名）──▶ 本服务 ──POST /api/pay/{aid}──▶ XorPay
  买家付款 → XorPay ──POST /xorpay/notify（MD5 签名）──▶ 本服务 ──POST notify_url（易支付回调）──▶ Dujiao

- /mapi.php 只在 Docker 内网可达（gateway 只对外转发 /xorpay/）
- /xorpay/notify 经 gateway 对外：验 XorPay 签名、核对金额，再按官方文档建议用平台单号向 XorPay 查一次
  （/api/query/{aoid}，确认已付款）才通知 Dujiao；查询失败或 Dujiao 没回 success 就回 XorPay 502，
  让 XorPay 按 1/2/4/16/64/300 分钟重试
- 订单记录存在 SQLite（DB_PATH），容器重启不丢
- 对接依据：https://xorpay.com/htdocs/xorpay.md（XorPay 官方对接说明）

环境变量（见 stack/.env.example）：
  XORPAY_AID          XorPay 后台的 aid      ＝ Dujiao 易支付渠道的「商户号」
  XORPAY_APP_SECRET   XorPay 后台的 app secret ＝ Dujiao 易支付渠道的「商户密钥」
  PUBLIC_BASE_URL     站点公网地址，如 https://shuweicao.org（XorPay 回调地址 = 它 + /xorpay/notify）
  XORPAY_API_BASE     默认 https://xorpay.com（本地测试可指向 mock_xorpay.py）
  XORPAY_EXPIRE       二维码有效秒数，默认 600（Dujiao 订单 15 分钟过期，别设太长）
  DUJIAO_NOTIFY_URL   找不到订单记录时的兜底回调地址，默认 http://dujiao-next:8080/api/v1/payments/callback
  LISTEN_PORT         默认 8080
  DB_PATH             默认 /data/bridge.db
"""
import hashlib
import hmac
import json
import os
import sqlite3
import threading
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PAY_TYPES = {"alipay": "alipay", "wxpay": "native"}  # 易支付 type → XorPay pay_type
MAX_BODY = 64 * 1024
NAME_MAX = 60

# 查单（/api/query/{aoid}）返回的状态。fee_error = 买家已付款，只是 XorPay 平台费没扣成（余额不足）
PAID_STATUSES = {"payed", "success", "fee_error"}
UNPAID_STATUSES = {"new", "not_exist", "expire"}

# XorPay 下单失败时的处理建议（来自官方对接说明的错误码表）
XORPAY_HINTS = {
    "fee_error": "XorPay 余额不足：去 xorpay.com 充值（平台手续费从余额扣）",
    "sign_error": "签名错误：检查 XORPAY_APP_SECRET 是否和 XorPay 后台一致（不能有空格）",
    "missing_argument": "缺少参数",
    "pay_type_error": "支付类型错误",
    "order_payed": "这笔订单已经付过款",
    "order_exist": "订单号已存在且参数不同",
    "order_expire": "订单已过期，请重新下单",
    "app_off": "XorPay 账号被冻结：联系 XorPay 客服",
    "aid_not_exist": "aid 不存在：检查 XORPAY_AID",
    "no_contract": "XorPay 还没签约",
    "no_alipay_contract": "支付宝还没签约",
    "wechat_api_error": "微信接口报错，可能被风控：联系 XorPay 客服",
}


def xorpay_hint(status, info=""):
    info = str(info or "")
    if status == "alipay_api_error":
        if "ACCESS_FORBIDDEN" in info:
            return "支付宝未签约：去支付宝 App（或签约邮件）完成签约"
        if "invalid-app-auth-token" in info:
            return "支付宝授权过期：XorPay 后台 → 支付宝资料 → 第 3 步扫码授权"
        return "支付宝接口报错：联系 XorPay 客服"
    return XORPAY_HINTS.get(status, "")


@dataclass
class Config:
    aid: str = ""
    secret: str = ""
    public_base_url: str = ""
    api_base: str = "https://xorpay.com"
    expire: int = 600
    fallback_notify_url: str = "http://dujiao-next:8080/api/v1/payments/callback"
    port: int = 8080
    db_path: str = "/data/bridge.db"

    @classmethod
    def from_env(cls):
        env = os.environ.get
        return cls(
            aid=env("XORPAY_AID", "").strip(),
            secret=env("XORPAY_APP_SECRET", "").strip(),
            public_base_url=env("PUBLIC_BASE_URL", "").strip().rstrip("/"),
            api_base=(env("XORPAY_API_BASE", "") or "https://xorpay.com").strip().rstrip("/"),
            expire=int(env("XORPAY_EXPIRE", "") or 600),
            fallback_notify_url=(env("DUJIAO_NOTIFY_URL", "") or cls.fallback_notify_url).strip(),
            port=int(env("LISTEN_PORT", "") or 8080),
            db_path=env("DB_PATH", "") or "/data/bridge.db",
        )


def log(event, **fields):
    print(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "event": event, **fields}, ensure_ascii=False), flush=True)


def md5(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest().lower()


def epay_sign(params, key):
    """与 Dujiao epay v1 完全一致：去掉空值和 sign / sign_type，按参数名排序拼成 k=v&k=v，末尾接密钥，MD5 小写。"""
    items = sorted((k, v) for k, v in params.items() if v != "" and k not in ("sign", "sign_type"))
    return md5("&".join(f"{k}={v}" for k, v in items) + key)


def xorpay_pay_sign(name, pay_type, price, order_id, notify_url, secret):
    return md5(name + pay_type + price + order_id + notify_url + secret)


def xorpay_notify_sign(aoid, order_id, pay_price, pay_time, secret):
    return md5(aoid + order_id + pay_price + pay_time + secret)


def same(a, b):
    return hmac.compare_digest(str(a).lower().encode(), str(b).lower().encode())


def money2(value):
    """'10' / '10.0' → '10.00'；非法或 <= 0 返回 None。"""
    try:
        d = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    if not d.is_finite() or d <= 0:
        return None
    return str(d.quantize(Decimal("0.01")))


class Store:
    COLS = ("out_trade_no", "pid", "type", "name", "money", "price", "notify_url", "aoid", "qr",
            "expires_at", "status", "created_at", "paid_at", "notified_at", "last_error")

    def __init__(self, path):
        if os.path.dirname(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        with self.lock:
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS orders (out_trade_no TEXT PRIMARY KEY, pid TEXT, type TEXT, name TEXT,"
                " money TEXT, price TEXT, notify_url TEXT, aoid TEXT, qr TEXT, expires_at INTEGER, status TEXT,"
                " created_at INTEGER, paid_at TEXT, notified_at INTEGER, last_error TEXT)")
            self.conn.commit()

    def get(self, out_trade_no):
        with self.lock:
            row = self.conn.execute("SELECT * FROM orders WHERE out_trade_no = ?", (out_trade_no,)).fetchone()
        return dict(row) if row else None

    def save(self, row):
        values = [row.get(c) for c in self.COLS]
        with self.lock:
            self.conn.execute(f"INSERT OR REPLACE INTO orders ({','.join(self.COLS)}) VALUES ({','.join('?' * len(self.COLS))})", values)
            self.conn.commit()

    def update(self, out_trade_no, **fields):
        if not fields:
            return
        sets = ", ".join(f"{k} = ?" for k in fields)
        with self.lock:
            self.conn.execute(f"UPDATE orders SET {sets} WHERE out_trade_no = ?", [*fields.values(), out_trade_no])
            self.conn.commit()


def post_form(url, params, timeout=15, use_env_proxy=True):
    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Content-Type": "application/x-www-form-urlencoded", "User-Agent": "shuweicao-xorpay-bridge/1"})
    opener = urllib.request.build_opener() if use_env_proxy else urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=timeout) as resp:
        return resp.status, resp.read(64 * 1024).decode("utf-8", "replace")


def get_json(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": "shuweicao-xorpay-bridge/1"})
    with urllib.request.build_opener().open(req, timeout=timeout) as resp:
        return json.loads(resp.read(64 * 1024).decode("utf-8", "replace"))


class Bridge:
    def __init__(self, cfg, store):
        self.cfg = cfg
        self.store = store

    def confirm_paid(self, aoid):
        """按官方文档建议，回调后用平台单号再查一次。返回 (True/False/None, 状态)，None = 查询失败。"""
        if not aoid:
            return False, "missing aoid"
        try:
            resp = get_json(f"{self.cfg.api_base}/api/query/{urllib.parse.quote(aoid, safe='')}")
        except Exception as e:  # noqa: BLE001 - 网络 / JSON 错误：让 XorPay 稍后重试
            return None, f"{type(e).__name__}: {str(e)[:120]}"
        status = str(resp.get("status", "")).strip()
        if status in PAID_STATUSES:
            return True, status
        if status in UNPAID_STATUSES:
            return False, status
        return None, status or "empty status"

    # ---------- Dujiao → 本服务：创建支付 ----------
    def create(self, p):
        cfg = self.cfg

        def fail(msg, **fields):
            log("mapi_rejected", reason=msg, **fields)
            return {"code": -1, "msg": msg}

        if not cfg.aid or not cfg.secret:
            return fail("转接服务未配置 XORPAY_AID / XORPAY_APP_SECRET")
        if not cfg.public_base_url:
            return fail("转接服务未配置 PUBLIC_BASE_URL")
        if p.get("pid", "") != cfg.aid:
            return fail("商户号与 XORPAY_AID 不一致", pid=p.get("pid", ""))
        if not same(p.get("sign", ""), epay_sign(p, cfg.secret)):
            return fail("签名错误（Dujiao 渠道的商户密钥要和 XORPAY_APP_SECRET 一致）")

        out_trade_no = p.get("out_trade_no", "").strip()
        ep_type = p.get("type", "").strip().lower()
        pay_type = PAY_TYPES.get(ep_type)
        price = money2(p.get("money", ""))
        if not out_trade_no or not pay_type or not price:
            return fail("参数不全或不支持", out_trade_no=out_trade_no, type=ep_type, money=p.get("money", ""))

        now = int(time.time())
        old = self.store.get(out_trade_no)
        if old and old.get("qr") and old.get("price") == price and int(old.get("expires_at") or 0) > now + 30:
            log("order_reused", out_trade_no=out_trade_no)
            return {"code": 1, "msg": "success", "trade_no": old.get("aoid") or out_trade_no, "qrcode": old["qr"], "payurl": old["qr"]}

        name = (p.get("name", "").strip() or out_trade_no)[:NAME_MAX]
        notify_url = cfg.public_base_url + "/xorpay/notify"
        form = {
            "name": name, "pay_type": pay_type, "price": price, "order_id": out_trade_no,
            "notify_url": notify_url, "expire": str(cfg.expire),
            "sign": xorpay_pay_sign(name, pay_type, price, out_trade_no, notify_url, cfg.secret),
        }
        try:
            status, body = post_form(f"{cfg.api_base}/api/pay/{urllib.parse.quote(cfg.aid)}", form)
            resp = json.loads(body)
        except Exception as e:  # noqa: BLE001 - 网络 / JSON 错误都按下单失败处理
            return fail(f"请求 XorPay 失败：{type(e).__name__}", out_trade_no=out_trade_no, detail=str(e)[:200])
        if resp.get("status") != "ok":
            status, info = str(resp.get("status", "")), resp.get("info", "")
            hint = xorpay_hint(status, info)
            return fail(f"XorPay 返回 {status}" + (f"：{hint}" if hint else ""), out_trade_no=out_trade_no, info=str(info)[:200])
        qr = str((resp.get("info") or {}).get("qr", "")).strip()
        aoid = str(resp.get("aoid", "")).strip()
        if not qr:
            return fail("XorPay 没有返回二维码", out_trade_no=out_trade_no)
        expires_in = int(resp.get("expires_in") or resp.get("expire_in") or cfg.expire)
        self.store.save({
            "out_trade_no": out_trade_no, "pid": cfg.aid, "type": ep_type, "name": p.get("name", ""),
            "money": p.get("money", ""), "price": price,
            "notify_url": p.get("notify_url", "").strip() or cfg.fallback_notify_url,
            "aoid": aoid, "qr": qr, "expires_at": now + expires_in, "status": "new", "created_at": now,
        })
        log("order_created", out_trade_no=out_trade_no, aoid=aoid, price=price, pay_type=pay_type)
        return {"code": 1, "msg": "success", "trade_no": aoid or out_trade_no, "qrcode": qr, "payurl": qr}

    # ---------- XorPay → 本服务：付款通知 ----------
    def notify(self, p):
        """返回 (HTTP 状态码, 响应文本)。200 = 告诉 XorPay 通知成功；其他 = 让 XorPay 稍后重试。"""
        cfg = self.cfg
        aoid, order_id = p.get("aoid", ""), p.get("order_id", "")
        pay_price, pay_time = p.get("pay_price", ""), p.get("pay_time", "")
        if not cfg.secret or not same(p.get("sign", ""), xorpay_notify_sign(aoid, order_id, pay_price, pay_time, cfg.secret)):
            log("notify_bad_sign", order_id=order_id)
            return 400, "sign error"

        row = self.store.get(order_id)
        if row:
            if money2(pay_price) != row.get("price"):
                log("notify_amount_mismatch", order_id=order_id, pay_price=pay_price, expected=row.get("price"))
                self.store.update(order_id, last_error=f"amount mismatch: paid {pay_price}, expected {row.get('price')}")
                return 400, "amount mismatch"
            if row.get("status") == "notified":
                log("notify_duplicate", order_id=order_id)
                return 200, "ok"
            params = {"pid": row["pid"], "trade_no": aoid, "out_trade_no": order_id, "type": row["type"],
                      "name": row.get("name") or "", "money": row["money"], "trade_status": "TRADE_SUCCESS"}
            notify_url = row.get("notify_url") or cfg.fallback_notify_url
        else:
            # 没有本地记录（比如数据卷丢了）：签名已验，照样通知 Dujiao，金额由 Dujiao 按付款记录核对
            log("notify_unknown_order_fallback", order_id=order_id, pay_price=pay_price)
            params = {"pid": cfg.aid, "trade_no": aoid, "out_trade_no": order_id, "type": "alipay",
                      "money": money2(pay_price) or pay_price, "trade_status": "TRADE_SUCCESS"}
            notify_url = cfg.fallback_notify_url

        # 官方文档建议：回调后再查一次，确认 XorPay 那边这笔确实已付款（防止密钥泄露后被伪造回调）
        paid, qstatus = self.confirm_paid(aoid)
        if paid is None:
            log("notify_query_failed", order_id=order_id, aoid=aoid, detail=qstatus)
            return 502, "query failed"
        if not paid:
            log("notify_not_paid", order_id=order_id, aoid=aoid, status=qstatus)
            if row:
                self.store.update(order_id, last_error=f"query status {qstatus}")
            return 400, "not paid"
        if qstatus == "fee_error":
            log("xorpay_fee_error", order_id=order_id, hint=XORPAY_HINTS["fee_error"])

        params["sign"] = epay_sign(params, cfg.secret)
        params["sign_type"] = "MD5"

        try:
            status, body = post_form(notify_url, params, use_env_proxy=False)
            ok = status == 200 and body.strip().lower() == "success"
            detail = f"HTTP {status} {body.strip()[:80]}"
        except Exception as e:  # noqa: BLE001
            ok, detail = False, f"{type(e).__name__}: {str(e)[:150]}"
        if ok:
            if row:
                self.store.update(order_id, status="notified", paid_at=pay_time, notified_at=int(time.time()), last_error=None)
            log("notify_forwarded", order_id=order_id, aoid=aoid, pay_price=pay_price)
            return 200, "ok"
        if row:
            self.store.update(order_id, status="paid", paid_at=pay_time, last_error=detail)
        log("notify_forward_failed", order_id=order_id, detail=detail)
        return 502, "forward failed"


def make_handler(bridge):
    class Handler(BaseHTTPRequestHandler):
        server_version = "xorpay-bridge"

        def log_message(self, fmt, *args):  # 统一用 log() 输出
            pass

        def _params(self):
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                raise ValueError("body too large")
            body = self.rfile.read(length).decode("utf-8", "replace") if length else ""
            params = {}
            for source in (urllib.parse.urlsplit(self.path).query, body):
                for k, v in urllib.parse.parse_qsl(source, keep_blank_values=True):
                    params[k] = v
            return params

        def _send(self, code, text, ctype="text/plain; charset=utf-8"):
            data = text.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _route(self):
            path = urllib.parse.urlsplit(self.path).path
            try:
                if path == "/healthz":
                    return self._send(200, "ok")
                if path == "/mapi.php":
                    result = bridge.create(self._params())
                    return self._send(200, json.dumps(result, ensure_ascii=False), "application/json; charset=utf-8")
                if path == "/xorpay/notify" and self.command == "POST":
                    code, text = bridge.notify(self._params())
                    return self._send(code, text)
                if path == "/submit.php":
                    return self._send(400, "请把 Dujiao 易支付渠道的交互方式设为「扫码」(qr)")
                return self._send(404, "not found")
            except Exception as e:  # noqa: BLE001
                log("handler_error", path=path, error=f"{type(e).__name__}: {str(e)[:200]}")
                return self._send(500, "internal error")

        do_GET = _route
        do_POST = _route

    return Handler


def make_server(cfg, store=None, host="0.0.0.0"):
    bridge = Bridge(cfg, store or Store(cfg.db_path))
    return ThreadingHTTPServer((host, cfg.port), make_handler(bridge))


def main():
    cfg = Config.from_env()
    server = make_server(cfg)
    log("started", port=cfg.port, aid_set=bool(cfg.aid), secret_set=bool(cfg.secret),
        public_base_url=cfg.public_base_url, api_base=cfg.api_base, expire=cfg.expire)
    server.serve_forever()


if __name__ == "__main__":
    main()
