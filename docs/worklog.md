# 工作记录

> 按时间倒序记录每次做了什么、改了哪里、怎么验证的、还剩什么。现状汇总看 [HANDOFF.md](../HANDOFF.md)，操作步骤看各篇 docs。
> 仓库是公开的：这里不写服务器 IP、后台路径、安全入口、任何密钥。

---

## 2026-11-24 ～ 11-25：支付宝收款（XorPay 个人接口，不用备案、不用营业执照）

分支 `stripe-test-mode`，提交：`02a70df`、`eb7f6c0`、`225b36e`（以及本节）。同一时间另一个会话做加密货币 / Stripe（见下一节），双方按文件分工、动服务器前互相打招呼，没有冲突。详细说明见 [05-alipay-xorpay.md](05-alipay-xorpay.md)。

### 1. 调研：不备案的站怎么收支付宝

- 用户发来两个同行。xuegaogx.cc（Dujiao-Next 改版）的公开配置里，支付宝渠道的提供方是 `xorpay`，扫码，单笔上限 ¥1000；loranai.top 页面提示"大于 1000 无法支付""支付宝付款请关闭 VPN"，特征相同（没在对方站下单，未百分百确认）
- XorPay：微信支付服务商 / 支付宝 ISV，用官方「小微商户」机制给个人开通当面付，**不要营业执照、网站不用备案**，钱直接进本人支付宝（非二清）。个人支付宝单笔 ¥1000、单日 ¥5 万；开通费 ¥100；官方费 0.38%（线下）/ 0.6%（线上）+ 平台费 0.6%～1.2%（从预充值余额扣）；30 天无交易会被收回权限
- 风险：收款实名绑定本人支付宝，卖账号类商品容易被风控冻结；付款页在国内，买家开 VPN 可能白屏

### 2. 方案：转接服务（不改 Dujiao 官方代码）

- Dujiao v1.5.4 没有 XorPay 渠道。读 Dujiao 源码确认它自带「易支付 v1」协议的细节：下单 `/mapi.php`、MD5 签名规则、回调字段、回复 `success`、回调核对金额和币种、不主动查单
- 新增 `stack/xorpay-bridge/bridge.py`（只用 Python 标准库），把 XorPay 转成易支付 v1；`docker-compose.yml` 加 `xorpay-bridge` 容器（`python:3.12-alpine`，脚本只读挂载）；gateway 只对外开放 `/xorpay/`，下单接口只在 Docker 内网；`stack/xorpay-setup.sh` 让用户在服务器上自己输入 aid / app secret（密钥不经过 agent）
- 安全：验 Dujiao 的签名和商户号；验 XorPay 回调签名、核对金额；**收到回调后再用 `/api/query/{aoid}` 向 XorPay 查单，确认已付款才转给商城**（11-25 按官方说明补上，防止密钥泄露后被伪造回调）；查单失败或商城没回 `success` 就回 XorPay 502，让它按 1/2/4/16/64/300 分钟重试；同一订单复用二维码；订单记录存 SQLite
- 下单失败时日志带处理建议（`fee_error` → 去充值、`ACCESS_FORBIDDEN` → 去支付宝签约、授权过期 → 后台第 3 步扫码授权等）

### 3. 验证

| 做了什么 | 结果 |
| --- | --- |
| 单元测试 `python3 -I stack/xorpay-bridge/test_bridge.py -v` | 13 个全部通过 |
| 本地：假 XorPay（`mock_xorpay.py`）+ 本地商城建「支付宝」渠道（易支付 → 转接服务）→ 前台下单 → 选支付宝 → 模拟付款 | 付款页出现二维码；订单「已完成」、自动发卡、买家页面自动显示卡密 |
| 本地异常场景 | 重复通知不重复发货；金额被改、伪造签名都被拒绝；**签名正确但查单说未付款**的回调被拒、商城没收到；外网访问不到 `/mapi.php`（几种绕路写法都落到商城首页） |
| 线上部署（`02-deploy-stack.sh` + 重建 `xorpay-bridge`；首次部署时重建过一次 gateway 加载 `/xorpay/` 路由） | 经 Cloudflare 访问 `/xorpay/notify` 用假签名返回 400；`/health` 正常；转接服务在跑，等用户填账号 |
| 线上服务器到 xorpay.com 的网络 | 可达，查单接口 1～2 秒返回（部分海外网络解析不了 xorpay.com，但服务器不受影响） |
| 11-25 按 XorPay 官方对接说明 <https://xorpay.com/htdocs/xorpay.md> 逐项核对 | 下单参数、金额 `"10.00"`、签名拼接顺序、回调验签、幂等、回 200 + ok 都一致。该说明开头有一段给 AI 的角色设定，只当资料，没照做 |

### 4. 用户开通进展

- 用户**没有营业执照**（也没有个体户执照）→ 走个人 / 小微商户开通，单笔上限 ¥1000
- 正在填 XorPay 的支付宝申请资料：办公照片（招牌 + 内景）和办公地址实际必填，拍居住或办公的地方即可；资料要真实（表单有承诺勾选）

### 5. 改动的文件

- 新增：`stack/xorpay-bridge/bridge.py`、`mock_xorpay.py`、`test_bridge.py`，`stack/xorpay-setup.sh`，`docs/05-alipay-xorpay.md`
- 修改：`stack/docker-compose.yml`（`xorpay-bridge` 服务）、`stack/gateway/default.conf.template`（`/xorpay/` 路由）、`stack/.env.example`（`XORPAY_*`）、`server/02-deploy-stack.sh`（复制转接服务和 `xorpay-setup.sh`）；README、HANDOFF、`docs/01`、`docs/02`、`docs/03` 里的 XorPay 段落

### 6. 还没做（需要用户本人操作，XorPay 密钥和线上后台不由 agent 代填）

1. XorPay 审核通过 → 点支付宝签约邮件 → XorPay 后台第 3 步扫码授权 → 充 ¥20 左右余额（平台费从余额扣）
2. 在自己电脑终端运行 `ssh -t root@<服务器IP> 'cd /opt/shuweicao && ./xorpay-setup.sh'`，输入 aid / app secret
3. 商城后台建「支付宝」渠道：易支付、扫码、网关 `http://xorpay-bridge:8080`、商户号 / 商户密钥 = aid / app secret、单笔上限 1000（脚本跑完会打印全部字段）
4. 小额实测（真实 XorPay 账号还没跑过一单）：转接服务日志依次出现 `order_created` → `notify_forwarded`，以商城订单「已完成」为准

---

## 2026-11-24 ～ 11-25：加密货币收款（BEpusdt）+ Stripe 回测 + 线上回调端点

分支 `stripe-test-mode`，提交：`25ae4af`、`8e4ac97`、`bfa57bf`、`cf50757`（以及本文件）。同一时间另一个会话在同一个文件夹里做支付宝（XorPay，见 [05-alipay-xorpay.md](05-alipay-xorpay.md)），双方按文件分工：改共享文件、提交、动服务器之前互相打招呼，没有冲突。

### 1. 调研：雪糕小店的加密货币支付怎么做的

- 雪糕小店（xuegaogx.cc）也是 Dujiao-Next（改过的版本），从公开配置看，加密货币渠道是 Dujiao 的 `epusdt` 提供方，对接的是**新版 Epusdt（GMPay 接口）**，和 BEpusdt 接口不兼容
- 我们用的是 **BEpusdt v1.24.4**（项目原定方案，自建、GPL-3.0）+ Dujiao 自带 BEpusdt 渠道的**收银台模式**（`order_mode: cashier`，调 BEpusdt `/api/v1/order/create-order`），效果一样：商城只有一个「USDT / USDC 加密货币」按钮，买家在收银台页面自选币种和网络。不改代码

### 2. 本地（用户 Mac）

| 做了什么 | 结果 |
| --- | --- |
| `docker compose up -d bepusdt`（只起这一个容器） | 启动成功，首次启动打印后台账号 / 密码 / 安全入口 / 对接令牌（存进 `stack/data/bepusdt-local-credentials.txt`，不进 Git） |
| BEpusdt 后台：应用 URI 填 `http://localhost:8090`；钱包管理加 3 条（USDT·TRC20、USDT·BEP20、USDC·Polygon，全用公认黑洞地址，只测流程） | 保存成功 |
| 商城后台建渠道 3「USDT / USDC 加密货币」（网关 `http://bepusdt:8080`、收银台模式、币种 `USDT,USDC`、法币 CNY、通知地址走 Docker 内网） | 结算页出现该按钮 |
| 前台下单 → 跳到 BEpusdt 收银台 → 选 USDT·BSC / USDT·TRON / USDC·Polygon | 都能出单：¥10 = 1.5 USDT/USDC，显示地址、二维码、20 分钟倒计时，可"返回重选" |
| BEpusdt 后台对订单「补单」（模拟到账，不花钱） | 回调商城 → 订单「已完成」、自动发卡；BEpusdt 记为「回调成功」 |

排查过的问题：

- **回调回复不一致？** Dujiao 处理成功回 `success`，BEpusdt 文档写要求 `ok`。一度以为会判失败（页面刷新太早看到"失败"），查 BEpusdt 源码 `app/task/notify/notify.go`：回复里含 `success` 或 `ok` 都算成功。曾在 gateway 加过一个改写回复的入口，确认不需要后已撤回（没提交）
- **BSC / Polygon 收不到款**：BEpusdt 默认节点（nodies.app）已收费，返回 403；免费公开节点（PublicNode、dRPC、BNB 官方、polygon-rpc.com）逐个实测，BEpusdt 不带合约地址地整块查转账，这些节点会拒绝 / 不给查历史块 / 限流。结论：BSC / Polygon 需要 Alchemy 等带 Key 的节点。**TRON 默认节点能用**（扫块成功率 100%）
- **汇率**：BEpusdt 自动同步市场汇率；2026-11 美元兑人民币约 6.68，¥10 ≈ 1.5 USDT，正确
- BEpusdt 只在有待付订单的链上扫块；买家选好网络时会先发一次「等待支付」通知，商城回 `fail`，属正常

### 3. 线上服务器

| 做了什么 | 结果 / 验证 |
| --- | --- |
| `/root/shuweicao` 拉到 `25ae4af`，重跑 `03-enable-site.sh` | 所有站点 80 / 443 都放行 `/.well-known/acme-challenge/`（从 `/var/www/html` 读） |
| 经 Cloudflare 访问探测文件 | http / https、主站 / pay 子域 4 个地址都 200 |
| `03-enable-site.sh --issue-pay-cert` | pay.shuweicao.org 新签 Let's Encrypt 证书，到期 2027-02-23，Nginx 已换用 |
| 主站证书续期改成 webroot（`certbot reconfigure`），原配置备份到服务器 `/root/` | `certbot renew --dry-run` 两张证书都成功。**修掉了一个隐患**：Cloudflare 会把 http 跳成 https，原来的续期方式大概率在 2027 年 1 月续期时失败，导致 2 月 13 日证书过期、网站打不开 |
| `/opt/shuweicao/.env` 只改 `BEPUSDT_TAG=8a91be6`（= v1.24.4，和 `latest` 同一镜像） | 版本锁定 |
| `docker compose up -d bepusdt` | v1.24.4 启动；首次凭据存进服务器 `/root/bepusdt-initial-credentials.txt`（600）；启动后立刻访问过一次，带凭据的"安装完成"页已不再显示 |
| 外网检查 | 商城 `/health` 正常；`/xorpay/notify` 假签名仍返回 400（支付宝入口没受影响）；pay.shuweicao.org 200 |
| 资源 | 512 MB 内存，五个容器都起来后可用约 205～239 MB，swap 用约 220 MB；磁盘剩约 1.0 GB（89%） |

### 4. Stripe

| 做了什么 | 结果 |
| --- | --- |
| 本地回测：重启 `stripe-listen.sh`，渠道汇率 0.14 → **0.15**（原值按 1 美元 = 7.14 元算，偏低约 6.5%），测试卡 4242 买一单 | Stripe 收 $1.50；回调 `stripe_webhook_processed … success`；订单完成、自动发卡 |
| 查 Dujiao 源码：Stripe 回调地址可以不带 `channel_id`（会用各 Stripe 渠道的签名密钥逐个验签） | 线上可以先建回调端点、再建渠道，部署指南已按此调整顺序 |
| 用户同意后，用 test 密钥在 Stripe 沙盒建线上回调端点 `we_1UfaROJ1vX3S1b8tygDduZvn`：`https://shuweicao.org/api/v1/payments/webhook/stripe`，订阅 `checkout.session.completed`、`…async_payment_succeeded`、`…async_payment_failed`、`…expired` | 已启用（test 模式）；签名密钥存在用户 Mac 的 `stack/data/stripe-prod-webhook-secret.txt`（不进 Git）；经 Cloudflare 探测该地址能到达商城（线上还没建渠道，回"支付渠道不存在"，正常） |

### 5. 改动的文件

- `server/nginx/shuweicao.conf`、`server/03-enable-site.sh`：webroot 证书验证、pay 子域单独证书、`--issue-pay-cert`
- `docs/00-local-setup.md` 第 8 节（加密货币本地）、`docs/02-tech-spec.md` 7.2（BEpusdt 技术细节）、`docs/03-deployment-guide.md` 第 8 步（线上步骤、Stripe 顺序）、`HANDOFF.md`、`README.md`
- `stack/.env.example`：`BEPUSDT_TAG=8a91be6`

### 6. 还没做（需要用户本人操作，线上后台和密钥不由 agent 代填）

1. 登录 BEpusdt 后台（凭据：服务器 `/root/bepusdt-initial-credentials.txt`）→ 改密码、改安全入口、重置对接令牌 → 应用 URI 填 `https://pay.shuweicao.org` → 加自己的 USDT·TRC20 收款地址（只填地址）→ 可选填 TronGrid Key
2. 登录商城后台 → 确认合规声明 → 建 BEpusdt 渠道、Stripe 渠道（填法见部署指南第 8 步）→ 建商品 / 导卡密
3. 各付一笔小额验收：USDT（TRC20 手续费约 1～2 USDT 的 TRX）和 Stripe 测试卡；以商城后台订单「已完成」为准
4. 以后要开 BSC / Polygon：注册 Alchemy 拿 Key 填进 BEpusdt「区块节点」，并建议服务器升到 1 GB
5. `stripe-test-mode` 分支还没合并到 `main`

---

## 2026-11-19 ～ 11-20：本地跑通、Stripe test 模式、上线部署

提交：`dbdc71e`、`b2f0ec6`、`b1c755c`（详见 HANDOFF 第 3 节）

- Mac 本地用 Docker 跑起整套系统（v1.5.4，端口 8088），修正文档里的配置键名、查初始密码的命令、脚本执行权限
- Stripe test 模式本地全流程跑通：测试卡付款 → 回调 → 自动发卡；重复回调不重复发货；伪造签名被拒；当地货币付款正常入账。新增 `stack/stripe-listen.sh`
- 部署到 shuweicao.org（替换原来的"形象画布"，用户同意）：Ubuntu 源装 Docker、修 `02-deploy-stack.sh` 漏复制主题 / gateway 的问题、复用已有 Let's Encrypt 证书、停用 image-gen（文件保留可恢复）
- 发现仓库是公开的（HANDOFF 已更正），推送前删掉了个人环境细节
