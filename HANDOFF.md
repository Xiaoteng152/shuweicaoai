# 交接文档：shuweicao 发卡站

> 更新于 2026-11-20 · 给接手的 agent / 开发者。先读本文，再按需读 `docs/`。

## 1. 项目一句话

基于开源 **Dujiao-Next**（v1.5.4，Go + Vue 3，GPL v3）做一个 AI 账号自动发卡站，第一个商品是 **GPT 成品号**。部署方式：Docker Compose，跑在 DigitalOcean，前面是 Cloudflare；外观用"天策式外挂主题"（白色 + 暖黄），不改官方代码。

- 仓库：https://github.com/Xiaoteng152/shuweicaoai （main 分支）。⚠️ 2026-11-20 查到仓库是**公开**的（之前写的"私有"不对），任何人可见，密钥和个人环境细节一律不要写进仓库
- 域名现状：shuweicao.org 已接入 Cloudflare（NS 已切、根域和 pay 子域都已解析），但**现在跑的是用户另一个网站**（"形象画布"，Next.js），商城还没部署上去
- 用户本地文件夹：`/Users/tengg/Desktop/my-project/shuweicao`（Mac，内容与仓库一致）
- 域名：`shuweicao.org`（Spaceship 注册，2027-09-03 到期，自动续费开）
- 服务器：DigitalOcean Droplet，SFO3，当前 512 MB（建议升 1 GB），IP 137.184.x.x
- 用户沟通语言：中文；偏好简单直接、少术语

## 2. 业务路线（用户确定的顺序）

| 阶段 | 内容 | 状态 |
| --- | --- | --- |
| 0 | 技术准备：Mac 本地用 Docker 跑通 | 🟡 2026-11-20 已在 Mac 跑起来并完成测试订单；还没验证 vault 主题、备份 |
| 1 | 部署上线 shuweicao.org | ⬜ 用户决定先不部署，先接国外支付 |
| 2 | 上架 GPT 成品号 | ⬜ 价格 / 货源 / 质保未定 |
| 3 | 国外支付：USDT（BEpusdt）→ Stripe | 🟡 Stripe：本地 test 模式全流程已跑通；还没上线 live，USDT 未配 |
| 4 | 国内备案 | ⬜ 需营业执照；**shuweicao.org 不能备案**（.org 未获工信部批复 + 境外注册商），需新 .com/.cn + 国内服务器 |
| 5 | 国内支付：支付宝官方 | ⬜ 需营业执照 + 企业备案域名；备选易支付 |

建议（已写进 spec）：阶段 2 上架时同时开 USDT，否则无法收款。

## 3. 已完成

- **文档**（`docs/`）：业务 spec、技术 spec、本地准备、部署指南（买什么 / 去哪接入 / 10 步上线）、竞品天策拆解
- **应用栈**（`stack/`）：`docker-compose.yml`（gateway + dujiao-next + redis + bepusdt）、`init.sh`、`backup.sh`、`upgrade.sh`、`.env.example`
- **服务器脚本**（`server/`）：初始化（swap / Docker / ufw / SSH 加固）、部署 stack、启用 Nginx + Cloudflare 源站证书、同步 Cloudflare IP
- **主题**（`stack/theme/` + `stack/gateway/`）：白色 + 暖黄，亮 / 暗两套；首页注入标题区、查单卡片、付款方式、"怎么购买"、售后联系；`preview.html` 静态预览已截图验证
- **竞品调研**：确认天策 = Dujiao-Next vault 模板 + 约 17 个外挂 JS/CSS + 自建 `/tc-stats` 接口
- **本地环境（2026-11-20）**：用户 Mac 上 `stack/` 已初始化并在运行（`docker compose up -d gateway`，即 redis + dujiao-next + gateway，bepusdt 没启动）。`TAG=v1.5.4`，`APP_PORT=8088`（8080 被用户本机另一个项目占用，别动它）。前台 http://localhost:8088 ，后台路径见 `stack/config/config.yml` 的 `web.admin_path`。合规声明已由用户本人确认
- **Stripe（test 模式，本地）**：用的是 Stripe 沙盒（美国，USD；正式账户资料未提交）。后台渠道 ID 1：`信用卡 / Card（Stripe）`，按 `USD` + 汇率 `0.14` 收款，成功 / 取消跳转都是 `http://localhost:8088/pay`。新增 `stack/stripe-listen.sh`（用 Stripe CLI 把回调转发到本机），`.env` 新增 `STRIPE_TEST_SECRET_KEY` / `STRIPE_CHANNEL_ID`（只给脚本用）。测试商品「Stripe 测试商品（勿买）」¥10，3 条假卡密已卖掉 2 条
  - 已验证：测试卡付款 → 回调 200 → 自动发卡 → 游客查单可见；重发同一事件不重复发货；伪造签名被拒；买家用当地货币（越南盾）付款正常入账
  - 详细做法：[00-local-setup 第 7 节](docs/00-local-setup.md)、[技术 spec 7.1](docs/02-tech-spec.md)、[部署指南第 8 步](docs/03-deployment-guide.md)

## 4. 未验证 / 已知风险（接手请优先关注）

| 项 | 说明 |
| --- | --- |
| `server/` 脚本没在真机跑过 | 只做了 `bash -n` 检查。`stack/init.sh` 已在 Mac 实跑通过。注意：文件同步后执行权限会丢，先 `chmod +x *.sh` |
| `config.yml` | 已按 v1.5.4 官方模板核对并在本地跑通（实际写法见 [00-local-setup 第 3 节](docs/00-local-setup.md)）。线上还要改 `server.mode: release`、CORS、`email`（SMTP）。`web.admin_path` 在 Docker 镜像里**生效**（模板注释说忽略，已过时） |
| 主题只在静态预览里验证 | gateway 注入已确认（首页 HTML 带上了 3 个主题文件，均 200）。但后台还没把前台模板切到 **vault**，真实效果未看。变量依据官方 `templates/vault/styles/vault.css`（`--bg`、`--red` 主色、`--gold`，作用域 `.vault-scope` / `body.vault-tokens`）|
| 容器权限 | Mac（Docker Desktop）上没问题，文件 600 也能读、镜像以 root 运行。Linux 服务器上待验证 |
| Stripe 回调失败也回 HTTP 200 | 验签失败时 body 里是业务码 400，HTTP 仍是 200，Stripe 后台显示投递成功、不会重试。上线验收以商城订单状态为准 |
| 游客付款跳回后补填凭据 | 在内置浏览器里第一单付完跳回 `/pay` 时，要求重新输入邮箱 + 订单密码才看到订单（游客凭据存在当前标签页的 sessionStorage）。第二单正常。上线后用真实浏览器 / 手机再看一次 |
| 本机代理 | 用户 Mac 开着代理，它时而连不上 Stripe，会让 Stripe CLI 卡在 "Getting ready…"；直连 Stripe 是通的。`stripe-listen.sh` 已自动改直连 |
| BEpusdt | 用 `v03413/bepusdt` 镜像、数据卷 `/var/lib/bepusdt`、容器端口 8080 映射到 8090；首次配置走它的 Web 向导，细节未实测 |
| Stripe | 转售账号类业务可能被判禁止行业；文档已提示 USDT 为主通道。现在用的是沙盒账户，正式账户还要提交资料审核 |
| 许可证 | 已确认 **GPL v3**（后台合规声明里写明）。fork 二次开发后对外提供服务前，评估开源义务 |

## 5. 访问与工具现状（重要，省得再踩坑）

- **GitHub MCP 插件**（Claude Github MCP Connector）：已安装到 `shuweicaoai`（仅此仓库），**可读写文本文件**（`push_files` / `create_or_update_file`）。**不能新建仓库**（403），**不能传二进制**（图片会损坏）
- **claude.ai 的 GitHub 账号关联未生效**：`add_repo` / `list_repos` 仍报 "no GitHub account linked"，所以无法 git clone。用户已在 GitHub 装了 Claude App（当前是 All repositories，建议改成仅 shuweicaoai），但 claude.ai 侧关联未完成
- **云端容器里的 `gh` 凭据失效**（GH_TOKEN invalid），Bash 无外网
- **用户 Mac 的 device_bash 隔离环境**：访问不了 GitHub（代理 403），且文件夹挂载失败；可用 `device_list_dir / device_stage_files / device_commit_files` 读写 `/Users/tengg/Desktop/my-project/shuweicao`
- **内置浏览器**：已登录用户的 GitHub
- Claude in Chrome 扩展：未连接
- **桌面版 Claude Code（2026-11-20）**：可直接读写用户 Mac 上的项目文件夹、运行 Docker 和 Stripe CLI（已 `brew install`）。本地文件夹已 `git init` 并关联 `origin`（ssh），`gh` 已登录仓库所有者账号，可直接 commit / push（含图片）

## 6. 待办（按优先级）

1. **决定仓库是否改为私有**（现在是公开的，业务文档对所有人可见）
2. **阶段 0 收尾**：后台把前台模板切到 vault 看主题实际效果；改管理员密码 + 开 TOTP；跑一次 `backup.sh`
3. **用户待拍板**：GPT 成品号的名称 / 价格 / 货源 / 质保；有无营业执照；Stripe 主体；售后 TG 和邮箱（`stack/theme/sw-config.js` 里现在是占位 `@your_tg_id`、`support@shuweicao.org`）；**Stripe 收款**：美元汇率定多少、是否只收银行卡（关掉银行转账 / 先买后付）、是否保留"按买家当地货币显示"
4. **阶段 1 准备**（用户操作）：Droplet 升 1 GB；Cloudflare 添加站点 + Spaceship 改 NS + 3 条 A 记录；生成源站证书；提交 Stripe 正式账户资料
5. **Stripe 上线**（部署之后）：按 [部署指南第 8 步](docs/03-deployment-guide.md) 建线上渠道和 Webhook 端点 → 测试卡跑通 → 换 live key + live Webhook → 真实小额验收
6. ~~补传两张图片~~、~~本地改动同步到仓库~~：2026-11-20 已从用户 Mac 用 git 推送

## 7. 已作废的东西（不要再用）

- 用户 Windows 电脑 `C:\Users\TengG\Desktop\shuweicao\deploy\`：旧的"单二进制 + systemd"方案
- claude.ai 上的在线文档《shuweicao.org 发卡站技术方案 Spec》：同样是旧方案，以仓库 `docs/` 为准

## 8. 关键参考

- Dujiao-Next：https://github.com/dujiao-next/dujiao-next （前台源码在 `frontend/user/src/`，vault 模板在 `templates/vault/`）
- Docker 部署文档：https://dujiao-next.com/deploy/docker-compose （镜像 `dujiaonext/dujiao-next:${TAG}`，挂载 `/app/config.yml`、`/app/db`、`/app/uploads`、`/app/logs`，健康检查 `/health`，首次管理员密码可由 `DJ_DEFAULT_ADMIN_PASSWORD` 留空自动生成并打印到日志）
- 竞品：https://tiancexai.com/ （拆解见 `docs/04-tiance-teardown.md`）
