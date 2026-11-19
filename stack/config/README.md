# config/

- `config.yml.example`：init.sh 从 Dujiao-Next 仓库下载的官方模板（对应 .env 里的 TAG 版本）
- `config.yml`：你实际使用的配置，含密钥，**不要提交到 Git、不要发到群里**

容器内挂载为只读的 `/app/config.yml`。改完后执行 `docker compose restart dujiao-next` 生效。
