# data_analysis_webui

## 安装与启动（推荐：使用脚本）

项目根目录下提供了 Windows 与 Linux 的一键安装、启动脚本。

### Windows

| 步骤 | 操作 |
|------|------|
| 安装 | 双击运行 `install.bat`，或在 cmd 中执行 `install.bat` |
| 启动 | 双击运行 `start.bat`，或在 cmd 中执行 `start.bat` |

### Linux / macOS

| 步骤 | 操作 |
|------|------|
| 安装 | 在终端执行 `chmod +x install.sh && ./install.sh` |
| 启动 | 执行 `chmod +x start.sh && ./start.sh` |

---

## 手动安装与启动

### 安装

```bash
python -m venv venv
source venv/bin/activate  # Windows 请用对应 activate 脚本
pip install -r requirements.txt
```

### 启动

```bash
python src/gradio_app.py
```

默认监听：`http://0.0.0.0:5600`。

---

## API 配置（仅内网 Ollama / vLLM）

本项目已转为企业内网离线部署场景，仅支持：

- Ollama（OpenAI 兼容接口）
- vLLM（OpenAI 兼容接口）

### 步骤

1. 将 `api/config.azure.json.example` 复制为 `api/config.azure.json`
2. 在 `Providers` 中配置你内网模型服务地址和模型名
3. 在 `Router.default` 中指定默认 provider/model

Ollama 示例：

```json
{
  "API_TIMEOUT_MS": 600000,
  "Providers": [
    {
      "name": "ollama",
      "api_base_url": "http://127.0.0.1:11434/v1",
      "api_key": "ollama",
      "models": ["qwen2.5:14b"]
    }
  ],
  "Router": { "default": "ollama,qwen2.5:14b" }
}
```

vLLM 示例：

```json
{
  "API_TIMEOUT_MS": 600000,
  "Providers": [
    {
      "name": "vllm",
      "api_base_url": "http://127.0.0.1:8000/v1",
      "api_key": "vllm",
      "models": ["Qwen/Qwen2.5-14B-Instruct"]
    }
  ],
  "Router": { "default": "vllm,Qwen/Qwen2.5-14B-Instruct" }
}
```

### 环境变量覆盖

- `DATA_ANALYSIS_CONFIG_PATH`：覆盖 LLM 配置文件路径（默认 `api/config.azure.json`）
- `DATA_ANALYSIS_OUTPUT_DIR`：覆盖报告输出目录（默认 `data/reports`）

---

## 使用说明

1. 打开 Gradio 页面后上传 Excel/Word/文本文件。
2. 在聊天框输入分析需求。
3. 若指标有歧义，按提示选择候选指标名称。
4. 报告生成后可预览并下载 docx。
