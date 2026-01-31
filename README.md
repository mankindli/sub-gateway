# Sub Gateway - 轻量订阅网关

为外贸客户分发代理节点的轻量级订阅网关系统，支持 v2rayN 和 Clash 双格式输出。

## 功能特性

- ✅ 按客户生成独立订阅链接
- ✅ 每个客户包含2个节点（主用加速 + 备用直连）
- ✅ 支持 v2rayN 和 Clash 两种订阅格式
- ✅ 应急覆盖（单客户/可选全局）
- ✅ Token 轮换/禁用
- ✅ 管理 API（Basic Auth）
- ✅ CLI 管理工具

## 快速开始

### 方式一：Docker Compose（推荐）

```bash
# 1. 配置环境变量
cp .env.example .env
vim .env  # 修改 ADMIN_PASSWORD 和 BASE_URL

# 2. 启动服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f
```

### 方式二：本地运行

```bash
# 1. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
export ADMIN_USERNAME=admin
export ADMIN_PASSWORD=your_password
export BASE_URL=http://localhost:8000

# 4. 启动服务
uvicorn app.main:app --reload
```

### 方式三：Systemd 服务

```bash
# 1. 复制项目到 /opt
sudo cp -r . /opt/sub-gateway

# 2. 创建虚拟环境并安装依赖
cd /opt/sub-gateway
sudo python3 -m venv venv
sudo ./venv/bin/pip install -r requirements.txt

# 3. 安装服务
sudo cp systemd/sub-gateway.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sub-gateway
sudo systemctl start sub-gateway
```

## 配置 Nginx (HTTPS)

```bash
# 1. 复制配置文件
sudo cp nginx/sub-gateway.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/sub-gateway.conf /etc/nginx/sites-enabled/

# 2. 修改域名
sudo vim /etc/nginx/sites-available/sub-gateway.conf

# 3. 申请 SSL 证书
sudo certbot certonly --webroot -w /var/www/certbot -d sub.yourdomain.com

# 4. 重启 Nginx
sudo nginx -t && sudo systemctl reload nginx
```

## 使用指南

### 创建客户

**方式一：CLI 工具**
```bash
python gatewayctl.py create-customer --name "客户A-张三"
```

**方式二：API**
```bash
curl -X POST http://localhost:8000/admin/customers \
  -u admin:your_password \
  -H "Content-Type: application/json" \
  -d '{
    "name": "客户A-张三",
    "nodes": {
      "primary": {
        "share": "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ=@transit.example.com:8388",
        "clash": {
          "type": "ss",
          "server": "transit.example.com",
          "port": 8388,
          "cipher": "aes-256-gcm",
          "password": "password123"
        }
      },
      "backup": {
        "share": "socks5://user:pass@direct.example.com:1080",
        "clash": {
          "type": "socks5",
          "server": "direct.example.com",
          "port": 1080,
          "username": "user",
          "password": "pass"
        }
      }
    }
  }'
```

### 更新节点配置

直接编辑 `config/customers.yml`，修改对应客户的 `nodes.primary` 或 `nodes.backup` 字段。客户刷新订阅后立即生效。

### 应急切换

当中转故障时，快速切换到备用节点：

```bash
# 设置应急覆盖（主节点指向备用线路）
python gatewayctl.py set-override \
  --token "客户token" \
  --primary-share "ss://备用节点分享链接"

# 恢复正常
python gatewayctl.py clear-override --token "客户token"
```

也可以通过 API：
```bash
# 设置覆盖
curl -X POST http://localhost:8000/admin/customers/{token}/override \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"primary": {"share": "ss://新的分享链接"}}'

# 清除覆盖
curl -X DELETE http://localhost:8000/admin/customers/{token}/override \
  -u admin:password
```

### Token 轮换

当怀疑 Token 泄露时：

```bash
python gatewayctl.py rotate-token --token "旧token"
```

旧 Token 立即失效，需要向客户发送新的订阅链接。

### 禁用客户

```bash
python gatewayctl.py disable-customer --token "客户token"
```

禁用后订阅接口返回 403。

## API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 订阅接口（公开）

| 接口 | 说明 |
|------|------|
| `GET /s/{token}/v2rayn` | v2rayN 格式订阅（Base64） |
| `GET /s/{token}/clash` | Clash 格式订阅（YAML） |

### 管理接口（需要 Basic Auth）

| 方法 | 接口 | 说明 |
|------|------|------|
| POST | `/admin/customers` | 创建客户 |
| GET | `/admin/customers` | 列出客户 |
| GET | `/admin/customers/{token}` | 获取客户详情 |
| PATCH | `/admin/customers/{token}` | 更新客户 |
| DELETE | `/admin/customers/{token}` | 删除客户 |
| POST | `/admin/customers/{token}/rotate` | 轮换 Token |
| POST | `/admin/customers/{token}/override` | 设置覆盖 |
| DELETE | `/admin/customers/{token}/override` | 清除覆盖 |

## 配置文件

### customers.yml 结构

```yaml
customers:
  - token: "32位随机字符串"
    name: "客户名称"
    enabled: true
    nodes:
      primary:
        share: "ss://... 或 socks5://..."  # v2rayN 使用
        clash:                              # Clash 使用
          type: ss
          server: example.com
          port: 8388
          cipher: aes-256-gcm
          password: xxx
      backup:
        share: "备用节点分享链接"
        clash:
          type: socks5
          server: example.com
          port: 1080
    override: null  # 应急覆盖，格式同 nodes
```

## 客户端使用

### v2rayN

1. 复制订阅链接：`https://sub.yourdomain.com/s/{token}/v2rayn`
2. v2rayN → 订阅 → 订阅设置 → 添加订阅
3. 粘贴链接，点击确定
4. 更新订阅

### Clash

1. 复制订阅链接：`https://sub.yourdomain.com/s/{token}/clash`
2. Clash → 配置 → 添加配置 → URL
3. 粘贴链接，下载配置

### 订阅二维码

将订阅链接生成二维码发给客户，客户扫码即可导入。以后变更只需更新订阅。

## 日志

日志文件位于 `logs/subscribe.log`，记录所有订阅访问：

```
2026-01-31 12:00:00 - sub_gateway - INFO - SUBSCRIBE | token=a1b2c3d4... | name=客户A | ip=1.2.3.4 | format=v2rayn | status=200 | ua=v2rayN/6.x
```

## 安全建议

1. **修改默认密码**：务必修改 `ADMIN_PASSWORD`
2. **使用 HTTPS**：配置 Nginx + Let's Encrypt
3. **限制管理接口**：可在 Nginx 中限制只允许特定 IP 访问 `/admin/`
4. **定期轮换 Token**：可疑泄露时立即轮换

## 目录结构

```
sub-gateway/
├── app/                    # 应用代码
│   ├── main.py            # 入口
│   ├── config.py          # 配置
│   ├── models.py          # 数据模型
│   ├── storage.py         # YAML 存储
│   ├── routers/           # 路由
│   └── services/          # 服务
├── config/                 # 配置文件
│   └── customers.yml      # 客户数据
├── logs/                   # 日志目录
├── nginx/                  # Nginx 配置
├── systemd/               # Systemd 配置
├── gatewayctl.py          # CLI 工具
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## License

MIT
