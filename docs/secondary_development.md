# 二次开发与模块配置指南（内网版）

本文面向企业内网离线部署场景，项目仅保留 **Ollama** 与 **vLLM(OpenAI 兼容接口)** 两种推理模式。

## 1. 项目结构总览

- `src/gradio_app.py`：Gradio WebUI 入口（多轮对话、报告预览、总结修订）。
- `src/main.py`：FastAPI 接口入口（`/health`、`/meta/options`、`/analyze/match`、`/analyze`）。
- `src/excel_parser.py`：Excel 读取与结构识别（日期列、数值列、单位）。
- `src/indicator_resolver.py`：指标名与列名的映射、歧义消解。
- `src/analysis.py`：时间窗口解析。
- `src/llm_client.py`：统一 LLM 调用层（仅 Ollama/vLLM）。
- `src/report_docx.py`：报告生成与追加。
- `src/settings.py`：配置路径与报告输出目录管理。
- `api/config.azure.json`：LLM 配置文件（本地文件，不入库）。

## 2. 配置机制

### 2.1 LLM 配置路径

默认读取 `api/config.azure.json`，可通过环境变量覆盖：

- `DATA_ANALYSIS_CONFIG_PATH=/your/path/config.json`

### 2.2 报告输出目录

默认 `data/reports`，可通过环境变量覆盖：

- `DATA_ANALYSIS_OUTPUT_DIR=/your/output/dir`

### 2.3 WebUI 端口

默认端口 5600，可通过环境变量覆盖：

- `GRADIO_SERVER_PORT=5601`

## 3. API 端口与端点

启动：

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

端点：

- `GET /health`：健康检查
- `GET /meta/options`：返回可调上下文工程项与配置项
- `POST /analyze/match`：分析前指标候选匹配
- `POST /analyze`：执行分析与报告生成

## 4. 接入 Ollama

1) 启动服务

```bash
ollama serve
```

2) 拉取模型

```bash
ollama pull qwen2.5:14b
```

3) 配置 `api/config.azure.json`

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

## 5. 接入 vLLM

1) 启动 vLLM OpenAI 接口（示例）

```bash
python -m vllm.entrypoints.openai.api_server --model Qwen/Qwen2.5-14B-Instruct --host 0.0.0.0 --port 8000
```

2) 配置 `api/config.azure.json`

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

## 6. 常见问题

- 404：请检查 `api_base_url` 是否是服务真实路径（通常要包含 `/v1`）。
- 超时：增大 `API_TIMEOUT_MS`，或使用更小模型。
- JSON 解析失败：可在提示词中强化“严格 JSON 输出”。
