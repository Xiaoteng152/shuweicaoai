# 支付宝收款：XorPay（不用备案、不用营业执照）

> 2026-11-24 · 本地已用假 XorPay 跑通全流程；线上等你开通 XorPay 后填账号即可用。业务背景见 [01-business-spec 第 5 节](01-business-spec.md)。

## 1. 为什么用 XorPay

同行（如 xuegaogx.cc，也是 Dujiao-Next）没有备案、没有自己签约支付宝，用的是 **XorPay 个人支付接口**：

- XorPay 是微信支付服务商 / 支付宝 ISV，用官方的「小微商户」机制帮个人开通收款，**个人用身份证就能开，不要营业执照，网站不用备案**
- 买家扫的是支付宝官方二维码，**钱直接进你自己的支付宝**（不是二清，XorPay 不经手资金）
- 同行页面上「支付宝单笔不超过 1000」「付款请关 VPN」都是这个接口的特征

## 2. 门槛、费用、限额（XorPay 官方说明，2026-11）

| 项 | 内容 |
| --- | --- |
| 谁能开 | 个人、个体户、企业都可以；个人用自己的支付宝 / 微信签约 |
| 开通费 | ¥100，开通成功不退 |
| 费率 | 支付宝官方 0.38%（每笔直接扣）+ XorPay 平台费：体验版 1.2%（¥0/月）、基础版 1%（¥10/月）、标准版 0.8%（¥30/月）、高级版 0.6%（¥60/月） |
| 平台费怎么扣 | 从 XorPay 账户**预充值余额**里扣；余额不足时下单会失败（`fee_error`） |
| 个人限额 | 支付宝单笔 ¥1000、单日 ¥5 万；微信单笔 ¥2 万、单日 ¥5 万。**办个体户执照后不限额** |
| 到账 | 支付宝即时到账（进签约支付宝的余额）；微信 T+1 到银行卡 |
| 保活 | 连续 30 天无交易，支付宝 / 微信会收回收款权限，重开再交 ¥100。每月做一笔测试单 |

每月流水约 ¥1 万以上时，高级版（0.6% + ¥60/月）比体验版（1.2%）划算。

## 3. 风险（先想清楚）

- 收款账户实名绑定**你本人**。被投诉或被判违规时，支付宝会降限额、延迟结算、冻结未结算资金、关闭收款；XorPay 明确说它没办法帮你解封
- 卖 GPT 成品号这类账号容易被判违规，买家号被封后投诉也会触发风控。商品页醒目位置放售后联系方式，纠纷先私下处理
- XorPay 首页写明：不接违法违规业务，发现后永久冻结并报警
- 付款页面在国内，买家开着 VPN 可能打不开或白屏，页面上要提醒（同行也这么写）
- 以上是常见情况，不构成法律意见

## 4. 怎么接到 Dujiao-Next（不改官方代码）

Dujiao-Next 官方版本没有 XorPay 渠道（雪糕是自己改了源码）。我们加了一个很小的转接服务 `stack/xorpay-bridge/bridge.py`（只用 Python 标准库），把 XorPay 转成 Dujiao **自带的「易支付」协议**：

```
买家下单 → Dujiao ──易支付 v1（/mapi.php，MD5）──▶ 转接服务 ──▶ XorPay 下单，拿到支付宝二维码
买家付款 → XorPay ──回调 https://shuweicao.org/xorpay/notify──▶ 转接服务 ──易支付回调──▶ Dujiao 自动发卡
```

- 转接服务是 `docker-compose.yml` 里的 `xorpay-bridge` 容器（官方 `python:3.12-alpine` 镜像，不用自己打包）
- 对外只开放 `/xorpay/` 这一个路径（gateway 转发）；下单接口 `/mapi.php` 只在 Docker 内网
- 安全：Dujiao → 转接服务验签名和商户号；XorPay → 转接服务验 XorPay 签名并核对金额；转接服务 → Dujiao 再签名，Dujiao 再核对金额和币种
- Dujiao 没回 `success` 时，转接服务回 XorPay 502，XorPay 会按 1/2/4/16/64/300 分钟重试 6 次
- 同一订单重复打开付款页，复用同一张二维码；二维码默认 10 分钟过期（`XORPAY_EXPIRE`，Dujiao 订单 15 分钟过期）
- 订单记录存在 `data/xorpay-bridge/bridge.db`（SQLite），日志：`docker compose logs -f xorpay-bridge`

## 5. 上线步骤

### 5.1 你来做：开通 XorPay

1. 到 xorpay.com 注册，选「个人」，按提示提交身份证、银行卡，用**你自己的支付宝**签约；交开通费 ¥100
2. 支付宝会发一封签约邮件，**点进去确认**（不确认会报 `ACCESS_FORBIDDEN`）
3. XorPay 账户里**预充一点余额**（平台费从这里扣，比如先充 ¥20）
4. 后台记下 `aid` 和 `app secret`（不要发到聊天里）

### 5.2 你来做：把账号填到服务器（一条命令）

在你自己电脑的终端运行，按提示输入 aid 和 app secret（输入 secret 时不显示）：

```bash
ssh -t root@<服务器IP> 'cd /opt/shuweicao && ./xorpay-setup.sh'
```

脚本会写入服务器的 `.env`、启动转接服务，并打印下一步后台要填的内容。

### 5.3 你来做：商城后台新建渠道

后台 → 支付渠道 → 新建：

| 字段 | 填写 |
| --- | --- |
| 名称 | `支付宝` |
| 提供方 / 渠道类型 | 易支付（epay）/ 支付宝（alipay） |
| 交互方式 | 扫码（qr） |
| 网关地址 | `http://xorpay-bridge:8080` |
| 易支付版本 / 签名类型 | `v1` / `MD5` |
| 商户号 | XorPay 的 aid |
| 商户密钥 | XorPay 的 app secret |
| 异步通知地址 | `http://dujiao-next:8080/api/v1/payments/callback`（走 Docker 内网，不经过 Cloudflare） |
| 同步跳转地址 | `https://shuweicao.org/pay` |
| 单笔最高金额 | `1000`，勾选「超出范围时隐藏」（个人身份的支付宝单笔上限） |

### 5.4 验收

自己买一个 ¥0.01～¥1 的测试商品，用支付宝扫码付款：后台订单变「已完成」、卡密自动发出、转接服务日志出现 `notify_forwarded`。**以商城后台订单状态为准**。

## 6. 本地测试（不用真 XorPay）

`stack/xorpay-bridge/mock_xorpay.py` 是一个假 XorPay：

```bash
cd stack
# .env 里：XORPAY_AID=mock-aid、XORPAY_APP_SECRET=<随便一串>、PUBLIC_BASE_URL=http://localhost:<APP_PORT>、
#         XORPAY_API_BASE=http://host.docker.internal:9999
MOCK_SECRET=$(grep '^XORPAY_APP_SECRET=' .env | cut -d= -f2-) python3 -I xorpay-bridge/mock_xorpay.py   # 保持运行
docker compose up -d xorpay-bridge && docker compose up -d --force-recreate gateway
```

后台按 5.3 建渠道（网关、通知地址相同，同步跳转用本地地址）→ 前台下单选支付宝 → 看到二维码后，用转接服务日志里 `order_created` 的 `out_trade_no` 模拟付款：

```bash
curl -X POST "http://127.0.0.1:9999/mock/pay?order_id=<out_trade_no>"            # 正常付款
curl -X POST "http://127.0.0.1:9999/mock/pay?order_id=<out_trade_no>&price=9.99" # 模拟金额被改，应被拒绝
```

单元测试：`python3 -I stack/xorpay-bridge/test_bridge.py -v`

2026-11-24 已验证：下单出二维码 → 模拟付款 → 回调经 gateway 到转接服务 → Dujiao 订单完成、自动发卡、买家页面自动显示卡密；重复通知不重复发货；金额被改、伪造签名都被拒绝；外网访问不到 `/mapi.php`。

## 7. 常见问题

| 现象 | 原因 / 处理 |
| --- | --- |
| 下单提示「XorPay 返回 fee_error」 | XorPay 余额不足，去充值 |
| 「no_alipay_contract」/「ACCESS_FORBIDDEN」 | 支付宝没签约，去邮箱点签约邮件 |
| 「签名错误」/「商户号与 XORPAY_AID 不一致」 | 后台渠道的商户号、商户密钥要和服务器 `.env` 里的一模一样；改完重跑 `xorpay-setup.sh` |
| 「转接服务未配置」 | 服务器上还没运行 `xorpay-setup.sh` |
| 付了款订单没变 | 看 `docker compose logs xorpay-bridge`：`notify_bad_sign`（密钥不一致）、`notify_amount_mismatch`（金额不符，人工核对后在后台手动确认）、`notify_forward_failed`（Dujiao 没回 success，XorPay 会自动重试） |
| 买家打不开付款页 / 白屏 | 让买家关掉 VPN |
| 超过 ¥1000 的订单没有支付宝 | 个人身份单笔上限；办个体户后把渠道单笔上限改大 |
