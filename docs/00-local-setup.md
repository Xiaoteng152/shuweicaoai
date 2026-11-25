# 技术准备：在 Mac 上跑起整套系统

> 目的：不花钱、不买服务器，先在本机把商城、后台、发货流程摸熟，确认 Dujiao-Next 满足需求。线上服务器用的是同一份 `stack/`，本地跑通，线上基本就不会出意外。

预计用时：30–60 分钟。

## 1. 装 Docker Desktop

1. 打开 https://www.docker.com/products/docker-desktop/ ，下载 Mac 版（Apple 芯片选 Apple Silicon，Intel 芯片选 Intel）
2. 安装后打开 Docker Desktop，等左下角显示 Engine running
3. 打开「终端」验证：

```bash
docker --version
docker compose version
```

## 2. 初始化

```bash
cd ~/Desktop/my-project/shuweicao/stack
chmod +x *.sh
./init.sh
```

`init.sh` 会：生成 `.env`（随机 Redis 密码）、建 `data/` 目录、下载官方 `config.yml` 模板，并打印**需要修改的配置项和已生成好的密钥**。把这段输出复制保存下来。

## 3. 改配置

```bash
open -e config/config.yml      # 用文本编辑打开，也可以用 VS Code
```

按 `init.sh` 打印的清单修改：三个密钥、`web.admin_path`、数据库路径 `/app/db/dujiao.db`、Redis（host 填 `redis`，密码填 `.env` 里的 `REDIS_PASSWORD`）。本地测试可以先不配邮件。

2026-11-20 在本机实际跑通时的写法（v1.5.4，模板里的键名都已核对）：

| 位置 | 改成 |
| --- | --- |
| `app.secret_key` / `jwt.secret` / `user_jwt.secret` | 各填一个 `openssl rand -hex 32`，三个不能相同（相同或用默认值会拒绝启动） |
| `server.trusted_proxies` | 在原来两行下面加 `- 172.16.0.0/12`（gateway 容器的网段） |
| `redis.host` / `queue.host` | 都改成 `redis`；两处的 `password` 都填 `.env` 里的 `REDIS_PASSWORD` |
| `database.dsn` | 保持 `./db/dujiao.db`（容器工作目录是 `/app`，即 `/app/db/dujiao.db`） |
| `email.enabled` | 本地先改 `false`；上线前配好 SMTP 再改回 `true` |
| `cors.allowed_origins` | 本地填 `http://localhost:<APP_PORT>`，线上填 `https://shuweicao.org` |
| `web.admin_path` | 改成随机路径，如 `/m-xxxxxxxxxxxx`。模板注释说"Docker 部署忽略此段"已过时：官方镜像就是前后台一体的版本，这一项**会生效** |

## 4. 启动

```bash
docker compose up -d
docker compose ps                                       # 四个容器都应为 running
docker compose logs dujiao-next | grep 随机密码          # 首次随机管理员密码（只显示一次；日志里是中文，grep password 搜不到）
curl http://localhost:8080/health                       # 健康检查
```

- 前台：http://localhost:8080
- 后台：http://localhost:8080 + 你设置的 `admin_path`
- 加密货币收银台 + 后台（BEpusdt，USDT / USDC）：http://localhost:8090 ，见下面第 8 节

**8080 端口被占用**（比如本机还跑着别的项目）：把 `.env` 里的 `APP_PORT` 改成别的（如 `8088`），下文的 8080 都换成它。

**第一次登录后台**：会弹出「合规使用声明确认」，必须由超级管理员**本人逐字键入**确认文字（不能粘贴）。不确认的话，支付渠道等支付功能一直不能用。

**忘了管理员密码**：

```bash
docker compose exec -it dujiao-next ./dujiao-next admin reset-password --username admin
```

**Apple 芯片**：官方镜像已提供 arm64 版本，正常无需处理。万一报 `no matching manifest for linux/arm64`，执行下面一行再 `docker compose up -d`（会用 Rosetta 模拟，稍慢但可用）：

```bash
export DOCKER_DEFAULT_PLATFORM=linux/amd64
```

**容器反复重启**：`docker compose logs --tail 100 dujiao-next` 看报错，多数是 config.yml 里的数据库路径或 Redis 配置不对；如果是 `permission denied`，执行 `chmod -R 777 data/db data/uploads data/logs` 后重启。

## 5. 本地要验证的事（技术准备的验收标准）

- [ ] 登录后台，改管理员密码，开启 TOTP 两步验证
- [ ] 熟悉后台：站点设置、商品分类、商品、卡密库存、订单、支付渠道
- [ ] 建一个测试商品「GPT 成品号（测试）」，导入 3 条假卡密，格式 `test1@example.com----pass1----2FA----备注`
- [ ] 前台用游客身份下单，确认订单页、查单流程
- [ ] 在后台把一笔订单手动标记为已付款，确认会自动发出一条卡密、库存减 1
- [ ] 卡密卖完后，商品自动显示缺货
- [ ] 后台把前台模板切换为 **vault**，刷新首页，确认已是白色 + 暖黄主题，首页顶部出现标题区、底部出现「怎么购买」
- [ ] 改 `theme/sw-config.js` 里的文案 → `.env` 的 `THEME_VERSION` 加 1 → `docker compose up -d gateway` → 刷新看到新文案
- [ ] 点右上角切换深色模式，确认深色下也是暖色调
- [x] Stripe 测试模式：2026-11-20 已在本机跑通，步骤见下面第 7 节
- [ ] 跑一次备份：`./backup.sh`（Mac 需先 `brew install gnupg`），确认 `backups/` 下生成了加密文件

## 6. 常用命令

| 操作 | 命令 |
| --- | --- |
| 启动 / 停止 | `docker compose up -d` / `docker compose down` |
| 看日志 | `docker compose logs -f dujiao-next` |
| 改配置后重启 | `docker compose restart dujiao-next` |
| 清空重来（删除所有本地数据） | `docker compose down && rm -rf data && ./init.sh` |
| 换版本 | `./upgrade.sh v1.5.4` |
| 本地测 Stripe 时转发回调 | `./stripe-listen.sh`（测试期间保持运行） |

## 7. Stripe 测试模式（本地）

> 2026-11-20 已跑通：测试卡付款 → Stripe 回调 → 自动发卡 → 游客查单看到卡密；同一事件重发不会重复发货；伪造签名的回调会被拒绝；买家用当地货币（Stripe 自动换算）付款也正常入账。

付款走 Stripe 官方收银台（Checkout）：买家点「提交订单并支付」会跳到 checkout.stripe.com，付完跳回商城 `/pay`。到账有两条路互为保险：

- **Webhook**：Stripe 主动通知商城（买家关掉页面也能到账）
- **跳回时主动查询**：买家回到 `/pay` 时，商城主动向 Stripe 查这一单的状态

### 7.1 准备

1. 安装 Stripe CLI：`brew install stripe/stripe-cli/stripe`
2. Stripe 后台（右上角是测试模式 / 沙盒）→ Developers → API keys，复制 `sk_test_...`
3. 填到 `stack/.env` 的 `STRIPE_TEST_SECRET_KEY=`（只给转发脚本用，不进 Git、不传进容器）
4. 打印本机的回调签名密钥（`whsec_...`，同一台电脑上一般不变）：`./stripe-listen.sh --print-secret`

### 7.2 后台建渠道

后台 → 支付渠道 → 新建：

| 字段 | 填写 |
| --- | --- |
| 名称 | `信用卡 / Card（Stripe）`（前台显示给买家看） |
| 提供方 / 渠道类型 | 官方（official）/ Stripe，交互方式：跳转（redirect，Stripe 只支持这个） |
| Secret Key | `sk_test_...` |
| Publishable Key | `pk_test_...`（可不填，跳转收银台用不到） |
| Webhook Secret | 上一步打印的 `whsec_...` |
| 成功跳转 / 取消跳转 | 都填 `http://localhost:<APP_PORT>/pay` |
| API 地址 | 默认 `https://api.stripe.com` |
| 目标币种 / 汇率 | `USD` / `0.15`（2026-11 美元兑人民币约 6.68，1 ÷ 6.68 ≈ 0.15）：商城按人民币标价，付款时按这个固定汇率换成美元收。汇率不会自动更新，要定期手动改 |
| 支付方式类型 | 留空 = 用 Stripe 后台开着的所有方式；填 `card` = 只收银行卡（含 Apple Pay / Google Pay） |

建好后记下渠道 ID（第一个是 1），对应 `.env` 的 `STRIPE_CHANNEL_ID`。

### 7.3 测一单

1. `./stripe-listen.sh` 开着（看到 `Ready!` 再下单）
2. 前台买一个测试商品 → 选 Stripe → 在 Stripe 收银台填测试卡 `4242 4242 4242 4242`，有效期填任意未来日期，CVC 任意三位
3. 预期：转发窗口出现 `checkout.session.completed ... [200]`；后台订单变「已完成」、卡密少一条；买家订单页显示卡密

其他测试卡：`4000 0000 0000 9995`（余额不足被拒）、`4000 0025 0000 3155`（要求 3D 验证）。

### 7.4 踩过的坑

- **转发卡在 `Getting ready...`**：开着代理（Clash 等）时，Stripe CLI 会走代理，代理连不上 Stripe 就一直卡住。`stripe-listen.sh` 已自动处理：代理不通、直连能通时改为直连
- **收银台默认显示买家当地货币**：Stripe 默认开了 Adaptive Pricing（自动换成当地货币）。商城记账仍是美元，已测过越南盾付款正常入账；不想要可在 Stripe 后台关掉
- **收银台里除了银行卡还有 Amazon Pay、Cash App Pay、美国银行转账、Klarna**：这是 Stripe 后台默认开的。银行转账要几天才到账，到账前不发货；发卡站建议只留银行卡（渠道里填 `card`，或在 Stripe 后台关掉其他方式）
- **回调验签失败时 HTTP 状态码仍是 200**（错误写在返回内容里），Stripe 后台看起来"投递成功"。所以验收要看商城后台订单是否真的变成已付款，不能只看 Stripe 后台

## 8. 加密货币收款（BEpusdt，USDT / USDC，本地）

> 2026-11-24 已在本机跑通：下单 → 跳到 BEpusdt 收银台 → 买家自己选币种（USDT / USDC）和网络 → 显示金额和收款地址 → 到账回调 → 自动发卡。到账这一步本地用 BEpusdt 后台的「补单」模拟（不真付钱）。

效果和雪糕小店一样：商城结算页只有一个「USDT / USDC 加密货币」按钮，币种和网络在 BEpusdt 的收银台页面里选。用的是 Dujiao 自带 BEpusdt 渠道的**收银台模式**（`order_mode: cashier`），不改代码。

### 8.1 启动 BEpusdt

```bash
docker compose up -d bepusdt
docker compose logs bepusdt        # 首次启动打印后台账号、密码、安全入口、对接令牌，只出现这一次，马上存好
```

后台：`http://localhost:8090/<安全入口>`。第一次打开安全入口会先显示一次"安装完成"页（同样是这些信息），之后才是登录页。

### 8.2 BEpusdt 后台设置

| 位置 | 填写 |
| --- | --- |
| 系统管理 → 基本设置 → API 设置 → 应用 URI | `http://localhost:8090`（线上填 `https://pay.shuweicao.org`）。收银台链接用它拼，不填会跳错 |
| 钱包管理 → 新增钱包 | 每个「币种 + 网络」一条：交易类型选如 `USDT・TRC20`、`USDT・BEP20`、`USDC・Polygon`，填**自己钱包的收款地址**（只填地址，永远不填私钥 / 助记词）；「其它通知」保持关闭 |
| 系统管理 → 区块节点 | TRON 默认节点能用，建议填 TronGrid API Key（免费）；**BSC / Polygon 的默认节点已不可用**，要填带 Key 的节点（见 8.5） |

本地测试时钱包地址用的是公认的黑洞地址（`T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb`、`0x000000000000000000000000000000000000dEaD`），只为看流程，千万别往里付款。

### 8.3 商城后台建渠道

后台 → 支付渠道 → 新建，提供方选 **BEpusdt**：

| 字段 | 填写 |
| --- | --- |
| 名称 | `USDT / USDC 加密货币` |
| 渠道类型 / 交互方式 | `bepusdt` / 跳转（收银台模式只支持跳转） |
| 支付网关 | `http://bepusdt:8080`（Docker 内网地址，商城直接找 BEpusdt 下单） |
| API Token | BEpusdt 的对接令牌 |
| 订单模式 | `cashier`（收银台模式：买家在付款页自选币种和网络） |
| 币种 | `USDT,USDC`（只开放这两种） |
| 法币 | `CNY`（按 BEpusdt 自动同步的市场汇率换算，¥10 ≈ 1.5 USDT） |
| 通知地址 | `http://dujiao-next:8080/api/v1/payments/callback`（Docker 内网，不经过公网 / Cloudflare） |
| 同步地址 | `http://localhost:<APP_PORT>/pay`（线上 `https://shuweicao.org/pay`） |

### 8.4 测一单（不花钱）

1. 前台买测试商品 → 选「USDT / USDC 加密货币」→ 跳到 BEpusdt 收银台 → 选币种、网络 → 看到金额、地址、二维码、20 分钟倒计时
2. BEpusdt 后台 → 交易订单 → 这一单点「补单」（强制标记已付款，**只在测试时用**）
3. 预期：BEpusdt 订单显示「交易成功 / 回调成功」；商城订单「已完成」、卡密少一条

### 8.5 踩过的坑

- **BSC / Polygon 收不到款**：BEpusdt 默认的 BSC、Polygon、Ethereum、Base 节点（nodies.app）已改成收费，返回 403；换成免费公开节点也不行——BEpusdt 扫块时不按合约过滤地查整块的转账记录，PublicNode 等免费节点会拒绝（要求指定地址 / 不给查历史块 / 限流）。要稳定收款，需注册节点服务商拿 Key（BEpusdt 官方推荐 Alchemy，免费套餐每月 3 亿计算单元），把带 Key 的地址填进「区块节点」
- **TRON 开箱即用**：默认节点扫块成功率 100%；长期用建议填 TronGrid API Key 防限流
- **只在有待付订单时扫块**：没有待付订单的链不会扫，不耗流量
- **回调回复**：Dujiao 处理成功回 `success`，BEpusdt 文档写要求回 `ok`，但它的代码两者都认（`app/task/notify/notify.go`），不用改
- **买家选好网络时，BEpusdt 会先发一次「等待支付」通知**，商城回 `fail`，属正常，不影响到账
