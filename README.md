# data_analysis_webui

## 安装与启动（推荐：使用脚本）

项目根目录下提供了 Windows 与 Linux 的一键安装、启动脚本。

### Windows

| 步骤 | 操作 |
|------|------|
| 安装 | 双击运行 `install.bat`，或在 cmd 中执行 `install.bat` |
| 启动 WebUI | 双击运行 `start.bat`，或在 cmd 中执行 `start.bat` |

### Linux / macOS

| 步骤 | 操作 |
|------|------|
| 安装 | 在终端执行 `chmod +x install.sh && ./install.sh` |
| 启动 WebUI | 执行 `chmod +x start.sh && ./start.sh` |

---

## 手动安装与启动

### 安装

```bash
python -m venv venv
source venv/bin/activate  # Windows 请用对应 activate 脚本
pip install -r requirements.txt
```

### 启动 WebUI

```bash
python src/gradio_app.py
```

默认监听：`http://0.0.0.0:5600`。

### 启动 API 服务（不使用 WebUI）

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8001
```

API 文档：`http://127.0.0.1:8001/docs`

---

## 配置与可调项总览

### 1) 上下文工程可调项（Prompt/Context 工程）

可调上下文来源与行为如下：

- 用户输入分析需求（主提示词）
- 上传的 Word/TXT 文档正文（补充资料）
- 原始文件信息上下文段（超限时自动置空）
- Excel 结构识别策略（启用/关闭 LLM 识别）
- 时间窗口解析（自然语言解析 / 手动覆盖）
- 指标歧义消解（候选指标二次确认）
- 综合总结提示词（可编辑并多轮修订）

对应代码入口：

- `src/gradio_app.py`：`_combine_prompt`、`_update_state_with_uploads`、`handle_message`
- `src/file_ingest.py`：上传内容解析与上下文拼接
- `src/llm_client.py`：原始文件上下文阈值计算
- `src/main.py`：`/analyze/match` 与 `/analyze` 的指标、时间窗口处理

### 2) 配置可调项

#### 2.1 配置文件

默认读取 `api/config.azure.json`（由 `api/config.azure.json.example` 复制）。

核心可调字段：

- `API_TIMEOUT_MS`：模型调用超时
- `Providers[].name`：`ollama` / `vllm`
- `Providers[].api_base_url`：OpenAI 兼容接口地址
- `Providers[].api_key`：鉴权 key（内网常用占位值）
- `Providers[].models`：模型列表
- `Router.default`：默认路由（`provider,model`）

上下文窗口相关字段：

- `RAW_FILE_CONTEXT_LIMIT_CHARS`：手动阈值（优先级最高）
- `MODEL_CONTEXT_WINDOW_CHARS`：模型窗口字符数
- `RAW_FILE_CONTEXT_RATIO`：自动阈值比例（默认 `0.35`）
- `Providers[].context_window_chars`
- `Providers[].model_context_window_chars`

#### 2.2 环境变量

- `DATA_ANALYSIS_CONFIG_PATH`：覆盖配置文件路径
- `DATA_ANALYSIS_OUTPUT_DIR`：覆盖报告输出目录
- `GRADIO_SERVER_PORT`：覆盖 WebUI 端口（默认 5600）

---

## 使用应用界面（WebUI）

1. 打开 Gradio 页面上传 Excel（必需），可附带 Word/TXT 文档。
2. 在输入框写分析需求（指标 + 时间范围 +分析目标）。
3. 系统若检测到指标歧义，会返回候选项，用户二次选择后继续。
4. 系统解析时间窗口、筛选数据、生成报告并在右侧预览。
5. 可继续多轮提问，系统将结果追加到同一份 docx。
6. 点击“生成综合总结”，把对话与报告内容综合生成结论。
7. 可勾选“将本条消息用于修改总结”进行总结迭代修订。

### WebUI 处理逻辑（简版）

- 文件上传：解析 Excel 与文档文本
- 上下文构造：主提示词 + 补充资料 + 原始文件信息（限长）
- 指标识别：先 LLM 解析，再规则兜底
- 时间窗口：LLM 解析并转换为实际日期区间
- 报告生成：图表与文本写入 docx，并支持多轮追加
- 总结生成：读取历史对话 + 报告摘要，输出综合结论

---

## API 调用（可脱离 WebUI）

支持。可直接通过 FastAPI 端口调用。

### API 端点

- `GET /healthz`：健康检查
- `GET /config/runtime`：运行时配置与可调项清单
- `POST /analyze/match`：指标歧义匹配
- `POST /analyze`：执行分析并生成报告

### 1) 健康检查

```bash
curl http://127.0.0.1:8001/healthz
```

### 2) 查询运行时配置

```bash
curl http://127.0.0.1:8001/config/runtime
```

### 3) 指标歧义匹配

```bash
curl -X POST "http://127.0.0.1:8001/analyze/match" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "excel_path=/path/to/data.xlsx" \
  -d "user_prompt=分析最近一年半钢胎产量趋势" \
  -d "sheet_name=Sheet1" \
  -d "use_llm_structure=true"
```

### 4) 生成报告

```bash
curl -X POST "http://127.0.0.1:8001/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "excel_path": "/path/to/data.xlsx",
    "user_prompt": "分析最近一年产量和销量趋势，并给出结论",
    "sheet_name": "Sheet1",
    "use_llm_structure": true,
    "selected_indicator_names": ["产量", "销量"]
  }'
```

### Python 调用示例

```python
import requests

base = "http://127.0.0.1:8001"

# 1) 歧义匹配
match_resp = requests.post(
    f"{base}/analyze/match",
    data={
        "excel_path": "/path/to/data.xlsx",
        "user_prompt": "分析最近一年产量趋势",
        "sheet_name": "Sheet1",
        "use_llm_structure": "true",
    },
    timeout=60,
)
match_resp.raise_for_status()
match_data = match_resp.json()

selected = None
if match_data.get("status") == "ambiguous":
    # 业务可弹窗给用户选择，这里演示默认选前两个
    selected = [c["display"] for c in (match_data.get("candidates") or [])[:2]]

# 2) 执行分析
analyze_resp = requests.post(
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
analyze_resp.raise_for_status()
print(analyze_resp.json())
```

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
