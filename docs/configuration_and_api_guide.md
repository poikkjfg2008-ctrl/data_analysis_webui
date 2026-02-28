# 配置设置、上下文工程与调用流程总览

本文回答三类问题：

1. 这个项目有哪些**上下文工程**可以调整。
2. 有哪些**配置项**可以调整。
3. 如何使用应用界面、内部处理逻辑如何运行、以及不使用 WebUI 时如何通过 API 调用。

---

## 1) 可调整的上下文工程（Context Engineering）

在本项目中，“上下文工程”主要体现在：如何构造 LLM 输入、如何缩小候选范围、如何控制表结构识别方式。

### 1.1 是否使用 LLM 识别 Excel 结构

- 开关：`use_llm_structure`
- 位置：
  - WebUI 复选框“使用 LLM 识别表结构”
  - API 参数 `AnalyzeRequest.use_llm_structure`
- 含义：
  - `true`：调用 LLM 识别日期列、数值列、单位等，适配更多异形表。
  - `false`：走启发式规则，速度可能更稳定，但对复杂表兼容更弱。

### 1.2 指标歧义澄清流程（两段式）

- 第一步：`POST /analyze/match`
  - 输入用户描述 + 指标候选列
  - 输出状态：`ok` / `not_found` / `ambiguous`
- 第二步：`POST /analyze`
  - 当 `ambiguous` 时，前端把用户选择后的 `selected_indicator_names` 传回，避免误匹配。

### 1.3 时间窗口上下文解析

- 通过 `parse_prompt` + `resolve_window` 从自然语言提取时间窗口。
- 可自动解析相对时间（如“最近一年”）或显式区间（如 `2024-01-01 至 2024-12-31`）。

### 1.4 多轮对话上下文

- WebUI 模式下，系统会把每轮分析追加到同一份 `session_report.docx`。
- 综合总结会基于对话历史自动拼接“对话记录”，并支持继续修订。

---

## 2) 可调整配置项

## 2.1 环境变量

| 变量名 | 默认值 | 作用 |
|---|---|---|
| `DATA_ANALYSIS_CONFIG_PATH` | `api/config.azure.json` | 覆盖 LLM 配置文件路径 |
| `DATA_ANALYSIS_OUTPUT_DIR` | `data/reports` | 覆盖报告输出目录 |
| `GRADIO_SERVER_PORT` | `5600` | 覆盖 WebUI 端口（未显式传 `--port` 时） |

## 2.2 `api/config.azure.json`

核心字段：

- `API_TIMEOUT_MS`: 模型请求超时毫秒数。
- `Providers[]`:
  - `name`: provider 名称（仅支持 `ollama` / `vllm`）
  - `api_base_url`: OpenAI 兼容接口地址
  - `api_key`: 鉴权 key（内网场景可填占位）
  - `models`: 可用模型列表
- `Router.default`: 默认 provider 与模型，格式 `provider,model`

### 推荐检查清单

1. `Router.default` 指向的 provider 必须在 `Providers[]` 中存在。
2. `api_base_url` 通常应包含 `/v1`。
3. 模型名要与服务端可见模型名完全一致。

---

## 3) WebUI 使用路径 + 内部处理逻辑

## 3.1 使用路径（用户视角）

1. 上传 Excel（可同时上传 docx/txt 作为补充上下文）。
2. 输入分析需求（指标 + 时间范围 + 关注点）。
3. 如有歧义，选择候选指标。
4. 获取报告预览并下载 docx。
5. 可继续多轮分析并生成综合总结。

## 3.2 处理逻辑（系统视角）

1. 读取上传文件，抽取 Excel 主数据与文本补充上下文。
2. 解析表结构（LLM 模式或启发式模式）。
3. 解析用户意图：指标、时间窗口、可选 sheet。
4. 若指标歧义，触发候选流程（`/analyze/match`）。
5. 过滤数据窗口，执行分析与图表生成。
6. 产出/追加 docx 报告，并在 WebUI 转为 HTML 预览。

---

## 4) 不使用 WebUI 时，API 端口调用方式

可以。推荐直接启动 FastAPI 并调用 HTTP 接口：

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

查看完整样例：

- `docs/api_examples.md`
- `examples/api_client_demo.py`
- `skills/data_analysis_api/SKILL.md`（给大模型的 API skill）

