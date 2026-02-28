# 二次开发与模块配置指南（内网版）

本文面向企业内网离线部署场景，项目仅保留 **Ollama** 与 **vLLM(OpenAI 兼容接口)** 两种推理模式。

## 1. 项目结构总览

- `src/gradio_app.py`：Gradio WebUI 入口。
- `src/main.py`：FastAPI 接口入口。
- `src/excel_parser.py`：Excel 读取与结构识别（日期列、数值列、单位）。
- `src/llm_client.py`：统一 LLM 调用层（仅 Ollama/vLLM）。
- `src/settings.py`：配置路径与报告输出目录管理。
- `api/config.azure.json`：LLM 配置文件（本地文件，不入库）。

## 2. 配置机制

### 2.1 LLM 配置路径

默认读取 `api/config.azure.json`，可通过环境变量覆盖：

- `DATA_ANALYSIS_CONFIG_PATH=/your/path/config.json`

### 2.2 报告输出目录

默认 `data/reports`，可通过环境变量覆盖：

- `DATA_ANALYSIS_OUTPUT_DIR=/your/output/dir`


### 2.3 原始文件信息上下文阈值（新增）

系统会将上传文档（TXT/DOCX）的原文作为“原始文件信息”候选上下文：

- `len(raw_text) <= limit_chars`：将原文注入该上下文段。
- `len(raw_text) > limit_chars`：该上下文段置空。

阈值 `limit_chars` 计算优先级：

1. `RAW_FILE_CONTEXT_LIMIT_CHARS`（手动绝对值，优先）
2. `MODEL_CONTEXT_WINDOW_CHARS * RAW_FILE_CONTEXT_RATIO`（自动）
3. 未配置时默认 `12000`

另外也支持 provider 级配置：

- `Providers[i].context_window_chars`
- `Providers[i].model_context_window_chars["模型名"]`

示例：

```json
{
  "MODEL_CONTEXT_WINDOW_CHARS": 128000,
  "RAW_FILE_CONTEXT_RATIO": 0.35,
  "Providers": [
    {
      "name": "vllm",
      "context_window_chars": 128000,
      "model_context_window_chars": {
        "Qwen/Qwen2.5-14B-Instruct": 128000
      }
    }
  ]
}
```


## 3. 接入 Ollama

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

## 4. 接入 vLLM

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

## 5. 常见问题

- 404：请检查 `api_base_url` 是否是服务真实路径（通常要包含 `/v1`）。
- 超时：增大 `API_TIMEOUT_MS`，或使用更小模型。
- JSON 解析失败：可在提示词中强化“严格 JSON 输出”。
