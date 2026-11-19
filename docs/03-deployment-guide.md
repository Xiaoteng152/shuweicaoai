# 部署文档：买什么、去哪接入、怎么上线

> 版本 v1 · 2026-11-19 · 前置：先完成 [00-local-setup.md](00-local-setup.md) 的本地验证
> 价格以各平台页面为准，下文只写量级。

## 1. 采购和注册清单

### 1.1 阶段 1–3 要用的（海外站）

| # | 服务 | 去哪 | 买 / 开什么 | 费用量级 | 什么时候 |
| --- | --- | --- | --- | --- | --- |
| 1 | 服务器 | DigitalOcean（cloud.digitalocean.com） | 现有 Droplet **Resize 到 Basic 1 GB / 1 vCPU**，并开 Backups | 约 $6/月 + 备份费 | 上线前 |
| 2 | 域名 | Spaceship（已有 shuweicao.org，2027-09-03 到期，已开自动续费） | 不用买，只改 NS | 已付 | 现在 |
| 3 | DNS / CDN / HTTPS | Cloudflare（dash.cloudflare.com） | Free 套餐，添加 shuweicao.org | 免费 | 现在 |
| 4 | 发信（卡密邮件） | Resend（resend.com）或其他 SMTP 服务 | 验证发信域名 shuweicao.org，拿 SMTP 账号 | 有免费额度 | 上线前 |
| 5 | 备份存储 | Cloudflare R2（同一个 Cloudflare 账号） | 建一个 bucket：shuweicao-backup，生成 API Token | 有免费额度 | 上线前 |
| 6 | 网站监控 | UptimeRobot（uptimerobot.com） | 免费版，监控首页和 pay 子域 | 免费 | 上线后 |
| 7 | USDT 收款钱包 | TronLink 等自己掌控私钥的钱包 | 新建一个专用收款钱包，记下 TRC20 地址 | 免费 | 阶段 2 |
| 8 | 链上数据接口 | TronGrid（trongrid.io） | 注册拿 API Key（给 BEpusdt 用） | 免费 | 阶段 2 |
| 9 | 信用卡收款 | Stripe（dashboard.stripe.com） | 注册并提交审核（通常需海外公司主体） | 按笔抽成 | **现在申请** |
| 10 | 售后 | Telegram | 客服账号；售后邮箱可用 Cloudflare Email Routing 转发 | 免费 | 上线前 |
| 11 | 代码仓库 | GitHub | 私有仓库存放本项目（不含 .env / config.yml） | 免费 | 现在 |

### 1.2 阶段 4–5 才用（国内备案和支付宝，有营业执照后再买）

| # | 服务 | 去哪 | 买 / 开什么 | 说明 |
| --- | --- | --- | --- | --- |
| 12 | 备案域名 | 阿里云万网 / 腾讯云 DNSPod | 新注册一个 **.com 或 .cn** | 用企业主体实名，实名信息与备案主体一致；.org 不能备案 |
| 13 | 国内服务器 | 阿里云 ECS / 轻量应用服务器（或腾讯云） | 中国内地地域，**包年包月 3 个月以上**，带公网带宽 | 备案的硬性要求 |
| 14 | ICP 备案 | 阿里云备案中心（beian.aliyun.com） | 企业备案 | 个人备案不能做在线交易 |
| 15 | 支付宝 | 支付宝开放平台（open.alipay.com） | 电脑网站支付 + 手机网站支付 | 需营业执照 + 已备案域名 |

## 2. 域名规划

| 域名 | 指向 | 用途 |
| --- | --- | --- |
| shuweicao.org | Droplet（经 Cloudflare 代理） | 商城前台、后台（隐藏路径）、API、支付回调 |
| www.shuweicao.org | 同上 | 301 跳转到主域名 |
| pay.shuweicao.org | 同上 | USDT 收银台（BEpusdt） |
| 发信记录（SPF / DKIM / MX） | 按发信服务给的值 | 卡密邮件不进垃圾箱 |
| 未来：xxx.com / xxx.cn | 国内服务器 | 备案后的国内站 |

## 3. 上线步骤

### 第 1 步：DigitalOcean

1. Droplet → 关机（Power Off）→ Resize → **CPU and RAM only** → 选 1 GB → 开机
2. Droplet → Backups → 开启
3. 确认 Mac 能免密登录：`ssh root@<服务器IP>`
   - 如果不能：在 Mac 执行 `ssh-keygen -t ed25519`（一路回车），再 `ssh-copy-id root@<服务器IP>`
4. 确认系统版本：`lsb_release -a`（建议 Ubuntu 22.04 或 24.04）

### 第 2 步：Cloudflare + Spaceship

1. Cloudflare 添加站点 shuweicao.org（Free），记下两个 NS
2. Spaceship → 域名管理器 → shuweicao.org → 名称服务器 → 自定义 → 填两个 NS
3. Cloudflare → DNS：加 3 条 A 记录（`@`、`www`、`pay` → 服务器 IP，橙色云开启）
4. SSL/TLS → 概述：**Full (strict)**；边缘证书：开 **Always Use HTTPS**
5. SSL/TLS → 源服务器 → 创建证书（主机名 `shuweicao.org, *.shuweicao.org`，15 年，PEM），**证书和私钥都复制保存**（私钥只显示一次）
6. 安全性 → WAF → 自定义规则：`URI 路径` 开头为 `/api/v1/payments` → 跳过「所有剩余自定义规则」和「速率限制」，排第一
7. 安全性 → 自动程序：**Bot Fight Mode 保持关闭**
8. 等 Cloudflare 显示站点「有效」（几分钟到几小时）

### 第 3 步：上传项目到服务器

在 Mac 终端：

```bash
cd ~/Desktop/my-project
rsync -av --exclude 'stack/.env' --exclude 'stack/config/config.yml' \
  --exclude 'stack/data' --exclude 'stack/backups' \
  shuweicao root@<服务器IP>:/root/
```

### 第 4 步：服务器初始化和部署

```bash
ssh root@<服务器IP>
cd /root/shuweicao/server
bash 01-server-init.sh          # 系统、swap、Docker、防火墙、SSH 加固
bash 02-deploy-stack.sh         # 部署到 /opt/shuweicao，生成 .env 和 config.yml，并打印修改清单
nano /opt/shuweicao/config/config.yml   # 按清单改；server.mode=release；CORS 只留 https://shuweicao.org
cd /opt/shuweicao && docker compose up -d
docker compose logs dujiao-next | grep -i password   # 首次管理员密码
curl -s http://127.0.0.1:8080/health
```

### 第 5 步：HTTPS

```bash
nano /etc/ssl/cloudflare/origin.pem    # 粘贴源站证书
nano /etc/ssl/cloudflare/origin.key    # 粘贴私钥
bash /root/shuweicao/server/03-enable-site.sh
```

打开 https://shuweicao.org 确认能访问。登录后台：改密码、开 TOTP。

### 第 6 步：发信

1. Resend（或其他服务）添加域名 shuweicao.org，把它给的 SPF / DKIM 记录加到 Cloudflare DNS（这几条**不要**开橙色云）
2. 拿到 SMTP 主机、端口、用户名、密码，填进 `config.yml` 的邮件部分
3. `docker compose restart dujiao-next`，下一笔测试单确认能收到卡密邮件

### 第 7 步：商品

1. 后台建分类和商品「GPT 成品号」，写清交付内容、质保和补发规则
2. 批量导入卡密，一行一个账号
3. 设置库存预警

### 第 8 步：支付（按顺序）

**USDT（先开）**

1. `docker compose logs bepusdt` 找安全入口 → 打开 `https://pay.shuweicao.org/<安全入口>` → 按向导建管理员
2. 添加 TRC20 收款**地址**（不要填私钥）、填 TronGrid API Key
3. 商城后台 → 支付渠道 → 新建 BEpusdt，填 BEpusdt 的地址和 Token
4. 自己付一笔最小金额，确认：链上到账 → 回调 → 自动发卡

**Stripe（审核通过后）**

1. 商城后台新建 Stripe 渠道（先 test key），记下页面给出的 Webhook 地址
2. Stripe → Developers → Webhooks → 添加该地址，只订阅支付成功 / 失败事件，拿到 `whsec_...` 填回
3. 用测试卡跑通 → 换 live key 和 live webhook → 真实小额再跑一次
4. 开启 Radar 和 3D Secure

### 第 9 步：备份、监控、定时任务

```bash
rclone config                      # 新建远端，名字 r2，类型 S3 → Cloudflare，填 R2 的 Access Key
/opt/shuweicao/backup.sh           # 手动跑一次
crontab -e
```

```cron
15 4 * * * /opt/shuweicao/backup.sh >> /var/log/shuweicao-backup.log 2>&1
30 4 * * 1 bash /root/shuweicao/server/cloudflare-ips.sh >> /var/log/cloudflare-ips.log 2>&1
```

- `/opt/shuweicao/.env` 里的 `BACKUP_PASSPHRASE` 和 config.yml 里的 `app.secret_key` **复制到密码管理器**
- UptimeRobot 加两个 HTTPS 监控：`https://shuweicao.org/health`、`https://pay.shuweicao.org`
- DigitalOcean → Monitoring → 告警：内存 > 85%、磁盘 > 80%

### 第 10 步：上线验收

- [ ] 重启服务器后四个容器自动起来（`reboot` 后 `docker compose ps`）
- [ ] 直接访问 `http://<服务器IP>` 不通
- [ ] `/admin` 打不开；隐藏路径能打开且要求 2FA
- [ ] USDT、Stripe 各跑一笔真实小额：付款 → 回调 → 自动发卡 → 收到邮件
- [ ] 重复回调不重复发货；超时未付订单自动关闭
- [ ] R2 里有备份文件，下载后能解密：`gpg -d xxx.tar.gz.gpg | tar -tz`

## 4. 阶段 4–5：备案和支付宝（有营业执照后）

1. 阿里云注册新域名（.com / .cn），企业实名认证
2. 购买中国内地 ECS 或轻量服务器（包年包月 ≥ 3 个月）
3. 阿里云备案中心提交企业 ICP 备案，按管局要求补材料；完成工信部短信核验
4. 备案通过后，在国内服务器上用同一套 `stack/` 部署（流程同第 3–5 步，HTTPS 证书改用阿里云免费证书或 Let's Encrypt）
5. 网站首页底部加备案号并链接到 beian.miit.gov.cn；按要求办理公安备案
6. 支付宝开放平台创建应用，签约电脑网站支付 + 手机网站支付，配置应用私钥 / 支付宝公钥，回调填新域名
7. 小额跑通后开放

> 注意：管局会审核网站实际内容，国内站卖什么要提前想好；不备案的替代方案是易支付，见业务 spec 第 3.1 节。

## 5. 月度费用（阶段 1–3）

| 项目 | 量级 |
| --- | --- |
| DigitalOcean 1 GB + 备份 | 约 $7–8/月 |
| 域名 | 已付（年费） |
| Cloudflare、R2、UptimeRobot、TronGrid、发信 | 免费额度内 0 |
| Stripe | 按笔抽成 |
| USDT | 链上转账手续费（买家付）；归集时自己付少量 |
