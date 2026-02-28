# 二次开发与模块配置指南（内网版）

本文面向企业内网离线部署场景，项目仅保留 **Ollama** 与 **vLLM(OpenAI 兼容接口)** 两种推理模式。

## 1. 项目结构总览

- `src/gradio_app.py`：Gradio WebUI 入口，负责上传、对话、报告预览、总结生成。
- `src/main.py`：FastAPI 接口入口，支持脱离 WebUI 的服务化调用。
- `src/excel_parser.py`：Excel 读取与结构识别（日期列、数值列、单位）。
- `src/file_ingest.py`：上传文件解析，构造补充资料与原始文件上下文。
- `src/llm_client.py`：统一 LLM 调用层（仅 Ollama/vLLM）。
- `src/settings.py`：配置路径与报告输出目录管理。
- `api/config.azure.json`：LLM 配置文件（本地文件，不入库）。

## 2. 可调整的上下文工程（Context Engineering）

### 2.1 输入上下文拼装

在 `src/gradio_app.py::_combine_prompt` 中，输入上下文由三段组成：

1. 用户输入需求（主任务）
2. 文档补充资料（Word/TXT 解析文本）
3. 原始文件信息上下文段（限长注入）

### 2.2 指标解析策略

- 先走 LLM 解析 `indicator_names`
- 再做规则匹配兜底（避免误匹配全部列）
- 存在歧义时，可通过 `/analyze/match` 返回候选项进行人机确认

### 2.3 时间窗口策略

- 支持自然语言相对时间（如“最近一年”）
- 支持绝对日期区间覆盖（UI 输入 `YYYY-MM-DD 至 YYYY-MM-DD`）

### 2.4 表结构识别策略

- `use_llm_structure=true`：用 LLM 识别日期列/指标列（泛化能力强）
- `use_llm_structure=false`：仅规则识别（性能稳定、成本低）

## 3. 配置机制

### 3.1 LLM 配置路径

默认读取 `api/config.azure.json`，可通过环境变量覆盖：

- `DATA_ANALYSIS_CONFIG_PATH=/your/path/config.json`

### 3.2 报告输出目录

默认 `data/reports`，可通过环境变量覆盖：

- `DATA_ANALYSIS_OUTPUT_DIR=/your/output/dir`

### 3.3 原始文件信息上下文阈值

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

### 3.4 其它常用配置

- `API_TIMEOUT_MS`：模型调用超时
- `Providers[].api_base_url`：模型服务地址
- `Providers[].models`：可用模型
- `Router.default`：默认 provider/model 路由
- `GRADIO_SERVER_PORT`：WebUI 端口

## 4. 应用界面使用与处理逻辑

### 4.1 WebUI 使用步骤

1. 上传 Excel（必需），可同时上传 Word/TXT。
2. 输入分析需求并发送。
3. 若出现指标歧义，按提示选择候选指标后继续。
4. 查看右侧报告预览并下载 docx。
5. 可进行多轮分析追加到同一报告。
6. 点击“生成综合总结”产出结论；可继续多轮修改总结。

### 4.2 处理逻辑（Pipeline）

1. 文件解析：读取 Excel + 文档文本。
2. 上下文构造：主提示词 + 补充资料 + 原始文件信息（限长）。
3. 意图解析：解析指标与时间窗口。
4. 数据过滤：根据时间窗口筛选数据。
5. 报告生成：写入图表、文字并回传预览。
6. 总结生成：基于对话与报告内容生成综合结论。

## 5. 不使用 WebUI 的 API 调用

可以。直接启动 FastAPI 即可服务化调用。

### 5.1 启动

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8001
```

### 5.2 端点

- `GET /healthz`
- `GET /config/runtime`
- `POST /analyze/match`
- `POST /analyze`

### 5.3 Python 代码示例

```python
import requests

base = "http://127.0.0.1:8001"

m = requests.post(
    f"{base}/analyze/match",
    data={
        "excel_path": "/path/to/data.xlsx",
        "user_prompt": "分析最近一年产量趋势",
        "sheet_name": "Sheet1",
        "use_llm_structure": "true",
    },
    timeout=60,
)
m.raise_for_status()
match_data = m.json()
selected = None
if match_data.get("status") == "ambiguous":
    selected = [c["display"] for c in (match_data.get("candidates") or [])[:1]]

a = requests.post(
    f"{base}/analyze",
    json={
        "excel_path": "/path/to/data.xlsx",
        "user_prompt": "分析最近一年产量趋势并给出建议",
        "sheet_name": "Sheet1",
        "use_llm_structure": True,
        "selected_indicator_names": selected,
    },
    timeout=600,
)
a.raise_for_status()
print(a.json())
```

## 6. 接入 Ollama

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

## 7. 接入 vLLM

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

## 8. 常见问题

- 404：请检查 `api_base_url` 是否是服务真实路径（通常要包含 `/v1`）。
- 超时：增大 `API_TIMEOUT_MS`，或使用更小模型。
- JSON 解析失败：可在提示词中强化“严格 JSON 输出”。
