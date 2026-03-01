# 部署指南 - Data Analysis WebUI

本文档提供完整的部署步骤，用于在本地或企业内网环境中部署 Data Analysis WebUI 项目，使用 Ollama/vLLM 作为离线 LLM 服务。

## 目录

- [系统要求](#系统要求)
- [快速部署（5分钟）](#快速部署5分钟)
- [详细部署步骤](#详细部署步骤)
- [验证部署](#验证部署)
- [常见问题](#常见问题)
- [生产环境优化](#生产环境优化)

---

## 系统要求

### 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 4核心 | 8核心+ |
| 内存 | 8 GB | 16 GB+ |
| 磁盘 | 10 GB 可用空间 | 50 GB+ SSD |
| GPU | 无 | NVIDIA GPU（可选，加速 vLLM） |

### 软件要求

- **操作系统**: Linux (Ubuntu 20.04+, Debian 11+) / macOS 10.15+ / Windows 10+
- **Python**: 3.9 或更高版本
- **LLM 服务**: Ollama 0.1.0+ 或 vLLM 0.2.0+

---

## 快速部署（5分钟）

### 1. 安装项目依赖

```bash
# 进入项目目录
cd /path/to/data_analysis_webui

# 创建虚拟环境并安装依赖
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置 LLM 服务

项目已预配置您的 Ollama 服务地址：`http://172.24.16.1:11434`

配置文件位置：`api/config.azure.json`

```json
{
  "Providers": [
    {
      "name": "ollama",
      "api_base_url": "http://172.24.16.1:11434/v1",
      "api_key": "ollama",
      "models": ["qwen3:14b"]
    }
  ],
  "Router": { "default": "ollama,qwen3:14b" }
}
```

### 3. 拉取 Ollama 模型

```bash
# 在 Ollama 服务所在机器执行
ollama pull qwen3:14b
```

### 4. 启动 API 服务

```bash
# 激活虚拟环境
source venv/bin/activate

# 启动服务（前台运行，用于测试）
uvicorn src.main:app --host 0.0.0.0 --port 8001

# 或后台运行（生产环境）
nohup uvicorn src.main:app --host 0.0.0.0 --port 8001 > api.log 2>&1 &
```

### 5. 验证部署

```bash
# 健康检查
curl http://127.0.0.1:8001/healthz

# 查看运行时配置
curl http://127.0.0.1:8001/config/runtime
```

预期输出：
```json
{"status":"ok"}
```

---

## 详细部署步骤

### 步骤 1: 系统准备

#### Linux/macOS

```bash
# 安装 Python 3.9+ (如未安装)
# Ubuntu/Debian:
sudo apt update
sudo apt install python3.9 python3.9-venv python3-pip

# macOS (使用 Homebrew):
brew install python@3.9

# 验证 Python 版本
python3 --version
```

#### Windows

1. 从 https://www.python.org/downloads/ 下载并安装 Python 3.9+
2. 安装时勾选 "Add Python to PATH"
3. 在命令提示符中验证：`python --version`

### 步骤 2: 安装项目

```bash
# 克隆或下载项目
cd /opt  # 或任意目录
# git clone <repository-url>  # 如使用 Git
# cd data_analysis_webui

# 使用项目提供的安装脚本（推荐）
chmod +x install.sh
./install.sh

# 或手动安装
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 步骤 3: 配置 Ollama 服务

#### 选项 A: Ollama 服务在同一台机器

```bash
# 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 启动 Ollama 服务
ollama serve

# 拉取模型
ollama pull qwen3:14b

# 测试模型
ollama run qwen3:14b "你好，请介绍一下你自己"
```

#### 选项 B: Ollama 服务在远程机器

项目已配置远程 Ollama 服务地址：`http://172.24.16.1:11434`

确保远程机器的 Ollama 服务可访问：

```bash
# 从项目机器测试连接
curl http://172.24.16.1:11434/v1/models

# 预期输出包含已安装的模型列表
```

### 步骤 4: 配置文件设置

编辑 `api/config.azure.json`：

```json
{
  "LOG": true,
  "HOST": "172.24.16.1",
  "PORT": 11434,
  "API_TIMEOUT_MS": 600000,
  "MODEL_CONTEXT_WINDOW_CHARS": 128000,
  "RAW_FILE_CONTEXT_RATIO": 0.35,
  "RAW_FILE_CONTEXT_LIMIT_CHARS": 0,
  "Providers": [
    {
      "name": "ollama",
      "api_base_url": "http://172.24.16.1:11434/v1",
      "api_key": "ollama",
      "models": ["qwen3:14b"],
      "context_window_chars": 128000
    }
  ],
  "Router": { "default": "ollama,qwen3:14b" }
}
```

**配置说明**：
- `API_TIMEOUT_MS`: LLM 调用超时时间（毫秒），默认 10 分钟
- `MODEL_CONTEXT_WINDOW_CHARS`: 模型上下文窗口大小
- `RAW_FILE_CONTEXT_RATIO`: 原始文件注入比例（0.35 = 35%）

### 步骤 5: 创建必要目录

```bash
mkdir -p data/reports
ls -la data/
```

### 步骤 6: 启动服务

#### API 模式（推荐用于生产）

```bash
# 前台运行（开发测试）
uvicorn src.main:app --host 0.0.0.0 --port 8001

# 后台运行（生产环境）
nohup uvicorn src.main:app --host 0.0.0.0 --port 8001 > api.log 2>&1 &

# 使用多 worker（高并发场景）
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001
```

#### WebUI 模式（交互式使用）

```bash
python src/gradio_app.py

# 访问 http://localhost:5600
```

### 步骤 7: 配置开机自启（可选）

#### 使用 systemd (Linux)

创建 `/etc/systemd/system/data-analysis-api.service`：

```ini
[Unit]
Description=Data Analysis API Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/opt/data_analysis_webui
Environment="PATH=/opt/data_analysis_webui/venv/bin"
ExecStart=/opt/data_analysis_webui/venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable data-analysis-api
sudo systemctl start data-analysis-api
sudo systemctl status data-analysis-api
```

---

## 验证部署

### 1. 基础健康检查

```bash
curl http://127.0.0.1:8001/healthz
# 预期: {"status":"ok"}
```

### 2. 配置验证

```bash
curl http://127.0.0.1:8001/config/runtime | jq
```

### 3. 完整功能测试

创建测试 Excel 文件（test_data.xlsx）并运行：

```bash
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --base-url http://127.0.0.1:8001 \
  --excel-path /path/to/test_data.xlsx \
  --user-prompt "分析最近一年的数据趋势"
```

预期输出：
```json
{
  "healthz": {"status": "ok"},
  "match": {"status": "ok", "indicator_names": ["产量"]},
  "selected_indicator_names": ["产量"],
  "analyze": {
    "report_path": "/path/to/report_20250301_143025.docx",
    ...
  }
}
```

---

## 常见问题

### Q1: 端口已被占用

**错误信息**: `Address already in use`

**解决方案**:
```bash
# 查找占用进程
lsof -i :8001
# 或
netstat -tlnp | grep 8001

# 终止进程或更换端口
uvicorn src.main:app --host 0.0.0.0 --port 8002
```

### Q2: 无法连接到 Ollama

**错误信息**: `Connection refused` 或 `Timeout`

**解决方案**:
```bash
# 1. 检查 Ollama 服务状态
curl http://172.24.16.1:11434/v1/models

# 2. 检查防火墙
sudo ufw allow from 172.24.16.0/24 to any port 11434

# 3. 检查 Ollama 监听地址（默认只监听 127.0.0.1）
# 在 Ollama 机器上设置环境变量允许远程访问
export OLLAMA_HOST=0.0.0.0:11434
ollama serve
```

### Q3: 模型未找到

**错误信息**: `model 'qwen3:14b' not found`

**解决方案**:
```bash
# 在 Ollama 服务机器上
ollama pull qwen3:14b
ollama list  # 验证模型已安装
```

### Q4: LLM 调用超时

**错误信息**: `Timeout after 600000ms`

**解决方案**:
```json
// 在 api/config.azure.json 中增大超时
{
  "API_TIMEOUT_MS": 1200000  // 20 分钟
}
```

### Q5: 依赖安装失败

**错误信息**: `No module named 'xxx'`

**解决方案**:
```bash
# 更新 pip
pip install --upgrade pip

# 单独安装失败的包
pip install package-name

# 如遇到编译错误，安装系统依赖
# Ubuntu/Debian:
sudo apt install python3-dev build-essential
```

---

## 生产环境优化

### 1. 性能优化

#### 使用 Gunicorn 多 Worker

```bash
gunicorn src.main:app \
  -w 4 \                    # Worker 数量（建议 CPU 核心数）
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8001 \
  --timeout 600 \           # 请求超时（秒）
  --worker-connections 1000 \
  --access-logfile - \      # 访问日志输出到 stdout
  --error-logfile -         # 错误日志输出到 stderr
```

#### 配置缓存（如需频繁分析同一文件）

考虑添加 Redis 缓存层，缓存 Excel 解析结果和 LLM 响应。

### 2. 监控与日志

#### 日志管理

```bash
# 创建日志目录
mkdir -p logs

# 启动服务时配置日志轮转
uvicorn src.main:app --host 0.0.0.0 --port 8001 \
  --log-config logging.conf \
  >> logs/api.log 2>&1
```

#### 日志轮转配置（logrotate）

创建 `/etc/logrotate.d/data-analysis-api`：

```
/path/to/data_analysis_webui/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload data-analysis-api > /dev/null 2>&1 || true
    endscript
}
```

### 3. 安全加固

#### 反向代理配置（Nginx）

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 文件上传大小限制
        client_max_body_size 100M;

        # 超时设置
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }
}
```

#### 添加 API 认证

建议在生产环境中添加 API Key 或 JWT 认证。可在 `src/main.py` 中添加中间件实现。

### 4. 备份与恢复

#### 定期备份配置和报告

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/data-analysis-$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# 备份配置
cp -r api/ "$BACKUP_DIR/"

# 备份最近7天的报告
find data/reports -mtime -7 -exec cp {} "$BACKUP_DIR/" \;

# 压缩
tar czf "$BACKUP_DIR.tar.gz" "$BACKUP_DIR"
rm -rf "$BACKUP_DIR"
```

#### 定时任务（crontab）

```bash
# 每天凌晨2点执行备份
0 2 * * * /path/to/backup.sh
```

---

## 附录

### A. 目录结构

```
data_analysis_webui/
├── api/                          # API 配置目录
│   ├── config.azure.json         # LLM 服务配置（主要配置文件）
│   └── config.azure.json.example # 配置模板
├── data/
│   └── reports/                  # 生成的报告输出目录
├── docs/                         # 文档目录
│   └── secondary_development.md  # 二次开发指南
├── skill_build/                  # 技能文件目录
│   └── the_skill_for_this_data_analysis/
│       ├── SKILL.md              # Agent 调用说明
│       └── scripts/
│           └── call_data_analysis_api.py  # API 调用脚本
├── src/                          # 源代码目录
│   ├── main.py                   # FastAPI 主程序
│   ├── gradio_app.py             # Gradio WebUI 界面
│   ├── llm_client.py             # LLM 客户端
│   ├── excel_parser.py           # Excel 解析
│   ├── analysis.py               # 数据分析逻辑
│   ├── report_docx.py            # 报告生成
│   └── ...
├── venv/                         # Python 虚拟环境（安装后生成）
├── requirements.txt              # Python 依赖列表
├── install.sh                    # 安装脚本（Linux/macOS）
├── install.bat                   # 安装脚本（Windows）
├── start.sh                      # 启动脚本（Linux/macOS）
├── start.bat                     # 启动脚本（Windows）
└── README.md                     # 项目说明
```

### B. 端口说明

| 端口 | 服务 | 用途 |
|------|------|------|
| 8001 | FastAPI | REST API 服务（默认） |
| 5600 | Gradio | WebUI 界面（默认） |
| 11434 | Ollama | LLM 服务（Ollama 默认） |

### C. 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DATA_ANALYSIS_CONFIG_PATH` | 配置文件路径 | `api/config.azure.json` |
| `DATA_ANALYSIS_OUTPUT_DIR` | 报告输出目录 | `data/reports` |
| `GRADIO_SERVER_PORT` | WebUI 端口 | `5600` |
| `OLLAMA_HOST` | Ollama 监听地址 | `127.0.0.1:11434` |

### D. 有用的链接

- 项目 README: `README.md`
- 技能文档: `skill_build/the_skill_for_this_data_analysis/SKILL.md`
- API 文档: http://127.0.0.1:8001/docs（启动服务后访问）
- Ollama 官方文档: https://ollama.com/docs
- FastAPI 文档: https://fastapi.tiangolo.com/

---

**部署完成后，建议先使用测试数据验证所有功能正常，再投入生产使用。**

如有问题，请查阅故障排查清单或查看项目日志文件。
