# data-analysis-api skill

## 用途

该 skill 用于让大模型通过 `data_analysis_webui` 的 FastAPI 接口执行“指标匹配 + 数据分析 + 报告生成”的标准流程。

## 适用场景

- 用户不使用 WebUI，希望直接 API 调用。
- 需要在 Agent/工作流系统中自动化生成分析报告。

## 前置条件

1. 服务已启动：`uvicorn src.main:app --host 0.0.0.0 --port 8000`
2. `api/config.azure.json` 已配置好 Ollama/vLLM。
3. 可访问 Excel 文件路径。

## 调用流程（必须遵守）

1. `GET /health`
   - 校验服务在线。

2. `GET /meta/options`
   - 读取当前可调配置和上下文工程选项，便于在回答中向用户解释“哪些可调”。

3. `POST /analyze/match`
   - 入参：`excel_path`, `user_prompt`, `sheet_name?`, `use_llm_structure?`
   - 如果返回 `status=ambiguous`：
     - 必须向用户展示 `candidates` 并请求确认；
     - 之后把确认结果填入 `selected_indicator_names` 再进入下一步。

4. `POST /analyze`
   - 入参 JSON：
     - `excel_path` (必填)
     - `user_prompt` (必填)
     - `sheet_name` (可选)
     - `output_dir` (可选)
     - `selected_indicator_names` (歧义时建议填写)
     - `use_llm_structure` (默认 true)

5. 输出
   - 返回 `report_path`, `time_window`, `indicator_names`, `sheet_name`, `date_column`。

## 推荐参数策略

- 默认 `use_llm_structure=true`，遇到复杂表头更稳。
- 若 LLM 结构识别超时，可降级 `use_llm_structure=false` 重试。
- 若用户需求未给指标名，先引导补充；或明确“全部指标”。

## 快速示例（Python）

```python
import requests

base = "http://127.0.0.1:8000"
prompt = "分析轮胎外胎产量最近一年趋势"
excel_path = "/path/to/your.xlsx"

requests.get(f"{base}/health", timeout=20).raise_for_status()
requests.get(f"{base}/meta/options", timeout=20).raise_for_status()

match = requests.post(
    f"{base}/analyze/match",
    params={"excel_path": excel_path, "user_prompt": prompt, "use_llm_structure": True},
    timeout=120,
)
match.raise_for_status()
match_data = match.json()

payload = {
    "excel_path": excel_path,
    "user_prompt": prompt,
    "use_llm_structure": True,
}

if match_data.get("status") == "ambiguous":
    payload["selected_indicator_names"] = [match_data["candidates"][0]["display"]]

result = requests.post(f"{base}/analyze", json=payload, timeout=600)
result.raise_for_status()
print(result.json())
```
