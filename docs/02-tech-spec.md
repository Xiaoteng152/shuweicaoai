# 技术栈 Spec

> 版本 v1 · 2026-11-19 · 业务需求见 [01-business-spec.md](01-business-spec.md) · 部署见 [03-deployment-guide.md](03-deployment-guide.md)

## 1. 选型结论

**不自研商城，直接用开源的 Dujiao-Next，以 Docker Compose 部署。** 第一阶段只做配置不写代码。Dujiao-Next 已自带推广返佣、钱包、礼品卡、开放 API、分销商（分站）模块；自带功能满足不了时再 fork 源码二次开发。竞品天策也是基于 Dujiao-Next 的 vault 模板做的，拆解见 [04-tiance-teardown.md](04-tiance-teardown.md)。

理由：发卡、库存、订单、查单、后台、支付回调这些 Dujiao-Next 都已内置；它的 8 种支付渠道已经覆盖我们要的支付宝、Stripe、USDT；官方镜像升级和回滚只需改版本号。

## 2. 技术栈

| 层 | 选型 | 说明 |
| --- | --- | --- |
| 商城 | Dujiao-Next（`dujiaonext/dujiao-next` 镜像） | 后端 Go（Gin + GORM），前台和后台都是 Vue 3；一个容器、一个端口（8080）同时提供前台、后台、API |
| 数据库 | SQLite（`/app/db/dujiao.db`） | 官方轻量方案。订单量大了再迁到 PostgreSQL（官方提供 `postgres:16-alpine` 方案） |
| 缓存 / 队列 | Redis 7（`redis:7-alpine`） | 只在 Docker 内部网络，不对外暴露端口 |
| 加密货币收款（USDT / USDC） | BEpusdt v1.24.4（`v03413/bepusdt:8a91be6`） | 自建，监听链上到账后回调商城；只放收款地址，不放私钥；收银台在 `pay.shuweicao.org` |
| 编排 | Docker Compose | 本地 Mac 和线上服务器用同一份 `stack/docker-compose.yml` |
| 反向代理 | Nginx（宿主机） | 443 端口，Cloudflare 源站证书；把 Cloudflare 传来的真实 IP 还原 |
| 主题网关 | Nginx 容器 `gateway`（`nginx:1.27-alpine`） | 商城前的一层，自动在页面插入 `stack/theme/` 的主题 CSS / JS（天策式外挂，见第 11 节） |
| CDN / DNS / 防护 | Cloudflare 免费版 | DNS、HTTPS、WAF、隐藏源站 IP |
| 服务器 | DigitalOcean Droplet，SFO3，Ubuntu | 建议 1 GB 内存 + 2 GB swap |
| 备份 | sqlite 在线备份 + gpg 加密 + rclone → Cloudflare R2 | 本地 7 天、远端 30 天 |
| 监控 | UptimeRobot + DigitalOcean 告警 | 网站存活 / 内存 / 磁盘 |

## 3. 架构

![架构图](architecture.png)

```
顾客 ──▶ Cloudflare（DNS·HTTPS·WAF）──▶ Nginx :443（宿主机）
                                          ├─ shuweicao.org      ─▶ 127.0.0.1:8080  gateway（插入主题）─▶ dujiao-next ─▶ redis（内部网络）
                                          │                                         └─ SQLite（data/db）
                                          └─ pay.shuweicao.org  ─▶ 127.0.0.1:8090  bepusdt
支付宝 / Stripe ──签名回调──▶ https://shuweicao.org/api/v1/payments/...
TRON 链上到账 ──▶ bepusdt ──回调──▶ dujiao-next
```

- 对公网只开 443（且 ufw 只放行 Cloudflare IP 段）和 22（SSH）
- 所有容器端口都绑定 127.0.0.1，外部无法直连

## 4. 环境

| 环境 | 位置 | 用途 | 域名 | 状态 |
| --- | --- | --- | --- | --- |
| local | 你的 Mac（Docker Desktop） | 技术准备、熟悉后台、试配置 | localhost:8080 | 阶段 0 |
| prod | DigitalOcean SFO3 | 正式海外站 | shuweicao.org / pay.shuweicao.org | 阶段 1 |
| prod-cn | 阿里云或腾讯云中国内地 | 备案后的国内站 + 支付宝官方 | 新的 .com / .cn 域名 | 阶段 4，视营业执照而定 |

暂不单独建测试环境：支付渠道一律先在 prod 用测试模式 / 小额跑通再放开。

## 5. 仓库结构

```
shuweicao/
├── README.md                 总览、路线图、进度
├── docs/
│   ├── 00-local-setup.md     技术准备：Mac 本地运行
│   ├── 01-business-spec.md   业务 spec
│   ├── 02-tech-spec.md       本文
│   ├── 03-deployment-guide.md 部署文档：买什么、去哪接入、怎么上线
│   ├── 04-tiance-teardown.md 竞品拆解
│   ├── architecture.png
│   └── theme-preview.png
├── stack/                    应用栈（本地和线上共用）
│   ├── docker-compose.yml
│   ├── .env.example          → .env（不进 Git）
│   ├── config/               → config.yml（不进 Git）
│   ├── theme/                白色 + 暖黄主题：sw-theme.css、sw-config.js（文案）、sw-home.js、preview.html
│   ├── gateway/              gateway 的 Nginx 配置（插入主题）
│   ├── init.sh               初始化 .env / 目录 / 配置模板
│   ├── backup.sh             加密备份
│   ├── upgrade.sh            升级 / 回滚
│   ├── stripe-listen.sh      本地测试 Stripe 时转发回调（线上不用）
│   ├── xorpay-setup.sh       填 XorPay 账号并启动转接服务
│   └── xorpay-bridge/        XorPay ⇄ 易支付 转接服务（bridge.py），附假 XorPay（mock_xorpay.py）和测试
└── server/                   只在线上服务器用
    ├── 01-server-init.sh     系统、Docker、防火墙、SSH 加固
    ├── 02-deploy-stack.sh    部署 stack 到 /opt/shuweicao
    ├── 03-enable-site.sh     启用 Nginx + HTTPS
    ├── cloudflare-ips.sh     同步 Cloudflare IP（真实 IP + 防火墙）
    └── nginx/shuweicao.conf
```

## 6. 关键配置（config.yml）

| 配置项 | 值 | 说明 |
| --- | --- | --- |
| `app.secret_key` | 随机 64 位十六进制 | 要和数据库一起备份 |
| `jwt.secret` / `user_jwt.secret` | 各自随机，三个密钥互不相同 | 后台 / 用户登录令牌 |
| `web.admin_path` | 随机路径，如 `/m-xxxxxxxxxxxx` | 默认 `/admin` 必须改。官方镜像是前后台一体版本，此项生效（模板注释说 Docker 忽略，已过时） |
| 数据库 | SQLite，`database.dsn: ./db/dujiao.db` | 容器工作目录 `/app`，即 `/app/db/dujiao.db` |
| Redis | `redis.host` 和 `queue.host` 都填 `redis`，port 6379，两处密码都同 `.env` | 容器名即主机名 |
| `bootstrap.default_admin_*` 或 `DJ_DEFAULT_ADMIN_*` | 初始管理员 | 密码留空则首次启动随机生成，只打印到控制台一次（`docker compose logs dujiao-next \| grep 随机密码`）；忘记用 `./dujiao-next admin reset-password --username admin` 重置 |
| `server.mode` | 线上 `release` | |
| `trusted_proxies` | `127.0.0.1`、`172.16.0.0/12` | 商城前有 gateway 容器，需信任 Docker 内网才能拿到顾客真实 IP |
| CORS | 线上只允许 `https://shuweicao.org` | |
| SMTP | 发信服务 | 发卡密邮件 |

健康检查：`GET /health`。

## 7. 支付对接（技术细节）

| 渠道 | Dujiao 渠道类型 | 回调 | 要点 |
| --- | --- | --- | --- |
| 加密货币（USDT / USDC） | BEpusdt，收银台模式（跳转到 `https://pay.shuweicao.org`） | BEpusdt → 内网 `http://dujiao-next:8080/api/v1/payments/callback` | BEpusdt 后台配收款地址 + 区块节点；商城里填内网网关 `http://bepusdt:8080` 和对接令牌。细节见 7.2 |
| Stripe | 官方 / Stripe（跳转） | `https://shuweicao.org/api/v1/payments/webhook/stripe?channel_id=<渠道ID>` | 先 test key 后 live key；细节见 7.1 |
| 支付宝（XorPay） | 易支付 v1（扫码），网关 = 内网 `http://xorpay-bridge:8080` | XorPay → `https://shuweicao.org/xorpay/notify` → 转接服务 → 内网 `http://dujiao-next:8080/api/v1/payments/callback` | 不用备案 / 执照；转接服务把 XorPay 转成易支付协议，不改官方代码。细节见 [05-alipay-xorpay.md](05-alipay-xorpay.md) |
| 支付宝（官方） | 支付宝官方 / 易支付 | `https://shuweicao.org/api/v1/payments/callback` | 官方需营业执照 + 备案域名 |

通用要求：只认签名校验通过的回调；同一订单重复回调不能重复发货（验收必测）；Cloudflare 对 `/api/v1/payments` 路径放行，且 **Bot Fight Mode 保持关闭**（免费版无法对单个路径豁免它）。

### 7.1 Stripe（2026-11-20 本地 test 模式已跑通，v1.5.4）

**流程**：下单 → 商城调 Stripe 建 Checkout Session（金额按渠道汇率换算）→ 买家跳到 checkout.stripe.com 付款 → 跳回 `success_url`（商城自动带上 `order_no` 等参数）→ 到账两条路互为保险：

1. Webhook：Stripe 推送事件，商城按 `whsec_` 验签后标记已付款并自动发货
2. 主动查询：买家回到 `/pay` 时，前端调 `/payments/:id/capture`，商城向 Stripe 查 Session 状态

**渠道配置（config_json）**

| 键 | 值 | 说明 |
| --- | --- | --- |
| `secret_key` | `sk_test_…` → 上线换 `sk_live_…` | 必填 |
| `publishable_key` | `pk_…` | 可空（跳转收银台用不到） |
| `webhook_secret` | `whsec_…` | 必填。本地用 `stripe-listen.sh --print-secret`；线上用 Stripe 后台该 Webhook 端点自己的密钥，两者不同 |
| `success_url` / `cancel_url` | `https://shuweicao.org/pay` | 必填。本地填 `http://localhost:<APP_PORT>/pay` |
| `api_base_url` | `https://api.stripe.com` | 默认 |
| `target_currency` / `exchange_rate` | `USD` / 如 `0.15`（2026-11 美元兑人民币约 6.68） | 商城人民币标价 → 按固定汇率收美元；不会自动更新，需定期手动改 |
| `payment_method_types` | 空或 `["card"]` | 空 = 用 Stripe 后台开着的全部方式（动态支付方式） |
| `webhook_tolerance_seconds` | 默认 300 | 回调时间戳允许误差 |

**Webhook 订阅事件**：`checkout.session.completed`、`checkout.session.async_payment_succeeded`、`checkout.session.async_payment_failed`、`checkout.session.expired`（`payment_intent.*` 商城也认，但 Checkout 流程不需要）。

**已验证**：测试卡 4242 付款 → 回调 200 → 订单完成、卡密 -1；`stripe events resend` 重发同一事件 → 日志 `payment_callback_idempotent_success`，不重复发货；伪造签名 → 拒绝；买家用当地货币付款（Stripe Adaptive Pricing，测的是越南盾）→ Session 仍按 USD 记账，商城正常入账。

**注意**

- 回调验签失败时商城返回 **HTTP 200**（业务码 400 写在 body 里），Stripe 后台会显示投递成功、也不会重试。上线后要看商城后台订单是否真的变成已付款，或看日志 `stripe_webhook_processed`
- Stripe 默认开着多种支付方式（Amazon Pay、Cash App Pay、美国银行转账、Klarna 等）。银行转账这类延迟到账的方式，到账前订单不发货；建议只留银行卡（`payment_method_types: ["card"]`，仍包含 Apple Pay / Google Pay）
- 上线可改用受限密钥（`rk_live_…`），只开 Checkout Sessions 写权限和 PaymentIntents 读权限，换上后先跑一单确认
- 本地开着代理时 Stripe CLI 可能连不上，`stripe-listen.sh` 会自动改为直连

### 7.2 加密货币：BEpusdt（2026-11-24 本地跑通，线上已部署待配置）

**版本**：BEpusdt v1.24.4，镜像 `v03413/bepusdt:8a91be6`（与 `latest` 同一镜像，`.env` 的 `BEPUSDT_TAG` 锁定）。GPL-3.0，自建，只放收款地址，不放私钥。

**流程**（Dujiao BEpusdt 渠道的收银台模式，调 BEpusdt `/api/v1/order/create-order`）：下单 → 商城在内网向 BEpusdt 建单 → 买家跳到 `https://pay.shuweicao.org/pay/checkout/<id>` → 选币种（USDT / USDC）和网络 → BEpusdt 给出金额（按自动同步的市场汇率，金额精确到 0.01）和收款地址，20 分钟内有效 → BEpusdt 扫块发现到账 → 回调商城 → 自动发卡。

**渠道配置（config_json）**

| 键 | 值 | 说明 |
| --- | --- | --- |
| `gateway_url` | `http://bepusdt:8080` | Docker 内网地址；不用公网域名 |
| `auth_token` | BEpusdt 对接令牌 | 首次启动打印在日志里；可在 BEpusdt 后台重置 |
| `order_mode` | `cashier` | 收银台模式（买家自选币种 / 网络）；`transaction` 是固定 `trade_type` 的旧模式 |
| `currencies` | `USDT,USDC` | 收银台只开放这两种 |
| `fiat` | `CNY` | 商城按人民币标价 |
| `notify_url` | `http://dujiao-next:8080/api/v1/payments/callback` | 内网回调，不经过 Cloudflare |
| `return_url` | `https://shuweicao.org/pay` | 付完跳回商城 |

**BEpusdt 侧**：「应用 URI」= `https://pay.shuweicao.org`（收银台链接用它拼）；每个「币种 + 网络」一条钱包；只在有待付订单的链上扫块。

**区块节点（重要）**

| 网络 | 默认节点 | 结论 |
| --- | --- | --- |
| TRON | `grpc.trongrid.io:50051` | 能用（实测扫块成功率 100%）；建议加 TronGrid API Key（免费）防限流 |
| BSC / Polygon / Ethereum / Base | `*-public.nodies.app` | **已不可用**（403 / 要求付费）。免费公开节点（PublicNode、dRPC、官方 RPC）也不行：BEpusdt 不带合约地址地 `eth_getLogs` 整块查转账，这些节点会拒绝 / 不给查历史块 / 限流。需要带 Key 的节点，如 Alchemy 免费套餐 |

**已验证（本地）**：收银台选 USDT·BSC / USDT·TRON / USDC·Polygon 都能出单；BEpusdt「补单」→ 回调商城 → 订单完成、卡密 -1；BEpusdt 记为回调成功。

**注意**

- Dujiao 处理成功回 `success`；BEpusdt 文档写要求 `ok`，但代码只要回复里含 `success` 或 `ok` 都算成功（`app/task/notify/notify.go`），无需改写
- 买家选好网络时 BEpusdt 先发一次「等待支付」通知，商城回 `fail`，属正常
- BEpusdt 首次启动的后台账号 / 密码 / 安全入口 / 对接令牌只在日志里出现一次；首次访问会显示一次"安装完成"页。线上首次登录后要改密码、改安全入口、重置对接令牌
- 内存：每条正在扫块的网络约 100 MB（BEpusdt 官方数据），官方建议 1 GB 内存；当前 512 MB 服务器开 1～2 条链可以，多了要升级

## 8. 安全

- ufw：80/443 只放行 Cloudflare IP，22 放行 SSH；容器端口只绑 127.0.0.1
- SSH 仅密钥登录；fail2ban；自动安全更新
- 后台：隐藏路径 + 强密码 + TOTP；可再加 Cloudflare Access
- `.env`、`config.yml`、证书私钥权限 600，不进 Git
- USDT 钱包私钥 / 助记词永不上服务器，定期归集到冷钱包

## 9. 二期开发方式（需要改代码时）

1. Fork `dujiao-next/dujiao-next` 到自己的 GitHub
2. 先确认许可证：官方文档写 MIT，仓库标注 GPL-3.0；若为 GPL，二次开发后对外提供服务需评估开源义务
3. 在 fork 里改代码，用 GitHub Actions 构建自己的镜像推到 GHCR（`ghcr.io/<你>/dujiao-next`）
4. 把 `docker-compose.yml` 里的镜像换成自己的，其余部署流程不变
5. 定期合并上游更新

二期候选功能：首页 / 商品页视觉重做（建议在 `frontend/user/src/templates/` 新增自己的模板）、合伙人等级价 + 累计消费自动升级（若自带分销功能不够）、账号状态检测工具、Codex 重置倒计时。

只改外观时也可以不 fork：像天策那样叠加自定义 CSS / JS。两种方式的优缺点见 [04-tiance-teardown.md](04-tiance-teardown.md)。

## 10. 容量与扩展

- 1 GB 内存可支撑当前容器（gateway、dujiao-next、redis、bepusdt、xorpay-bridge）；内存长期超过 80% 再升 2 GB
- 2026-11-25 线上仍是 512 MB（+2 GB swap）：五个容器都起来后 available 约 239 MB、swap 用了约 220 MB；磁盘剩约 1.0 GB（89%）。BEpusdt 每扫一条链约 +100 MB，加 BSC / Polygon 前建议先升 1 GB
- 订单量上来后：SQLite → PostgreSQL；备份改为 `pg_dump`
- 国内站上线时：同一套 `stack/` 部署到国内服务器，数据是否共用另行设计（两个站独立运营最简单）

## 11. 主题（白色 + 暖黄，天策式外挂）

| 文件 | 作用 |
| --- | --- |
| `stack/theme/sw-theme.css` | 覆盖 vault 模板的颜色变量（`--bg`、`--red` 主色、`--gold`…），亮色 / 暗色各一套；修正黄底白字；首页区块样式 |
| `stack/theme/sw-config.js` | 首页文案、按钮、付款方式、售后联系方式 —— **日常只改这个** |
| `stack/theme/sw-home.js` | 在首页上方插入标题区 + 查单卡片 + 付款方式，下方插入"怎么购买" + 售后联系；离开首页自动移除 |
| `stack/theme/preview.html` | 不启动系统也能看配色的静态预览 |
| `stack/gateway/default.conf.template` | gateway 用 `sub_filter` 在每个页面 `</head>` 前插入上面三个文件 |

为什么比天策稳：天策替换了官方编译后的页面文件，官方每次升级都要重做；我们只覆盖官方公开的颜色变量，并在首页根节点插入独立区块，官方升级后通常无需改动。

前提：后台「站点设置」里把前台模板切换为 **vault**。

更新主题：改完 `theme/` 下的文件 → `.env` 里 `THEME_VERSION` 加 1 → `docker compose up -d gateway`。
