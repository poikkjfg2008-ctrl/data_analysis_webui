# API 调用示例（curl + Python）

## 1. 启动服务

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## 2. 健康检查

```bash
curl -s http://127.0.0.1:8000/health
```

预期返回：

```json
{"status":"ok"}
```

## 3. 查看可调上下文工程与配置项

```bash
curl -s http://127.0.0.1:8000/meta/options | python -m json.tool
```

## 4. 指标歧义匹配（推荐先调用）

```bash
curl -s -X POST "http://127.0.0.1:8000/analyze/match" \
  --data-urlencode "excel_path=/path/to/your.xlsx" \
  --data-urlencode "user_prompt=分析轮胎外胎产量最近一年趋势" \
  --data-urlencode "sheet_name=Sheet1" \
  --data-urlencode "use_llm_structure=true" | python -m json.tool
```

如果返回 `status=ambiguous`，请读取 `candidates` 让用户确认后再调 `/analyze`。

## 5. 生成报告

```bash
curl -s -X POST "http://127.0.0.1:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "excel_path": "/path/to/your.xlsx",
    "user_prompt": "分析轮胎外胎产量最近一年趋势",
    "sheet_name": "Sheet1",
    "use_llm_structure": true,
    "selected_indicator_names": ["轮胎外胎产量"]
  }' | python -m json.tool
```

返回中 `report_path` 即生成的 docx 路径。

## 6. Python requests 示例

```python
import requests

BASE = "http://127.0.0.1:8000"
excel_path = "/path/to/your.xlsx"
user_prompt = "分析轮胎外胎产量最近一年趋势"

# 1) match
match_resp = requests.post(
    f"{BASE}/analyze/match",
    params={
        "excel_path": excel_path,
        "user_prompt": user_prompt,
        "sheet_name": "Sheet1",
        "use_llm_structure": True,
    },
    timeout=120,
)
match_resp.raise_for_status()
match_data = match_resp.json()

selected = None
if match_data.get("status") == "ambiguous":
    # 实际场景由用户从候选里选，这里示意选第一个
    cands = match_data.get("candidates") or []
    if not cands:
        raise RuntimeError("歧义状态但没有候选")
    selected = [cands[0]["display"]]

# 2) analyze
analyze_payload = {
    "excel_path": excel_path,
    "user_prompt": user_prompt,
    "sheet_name": "Sheet1",
    "use_llm_structure": True,
}
if selected:
    analyze_payload["selected_indicator_names"] = selected

analyze_resp = requests.post(
    f"{BASE}/analyze",
    json=analyze_payload,
    timeout=600,
)
analyze_resp.raise_for_status()
print(analyze_resp.json())
```

