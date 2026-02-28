# API 配置与调用说明（仅内网 Ollama / vLLM）

本目录下的真实配置文件（含 API Key 等）已被 `.gitignore` 忽略，不会提交到 Git。

## 1. 本地配置文件

克隆仓库后，根据范例文件创建本地配置：

1. 复制 `config.azure.json.example` 为 `config.azure.json`
2. 按你内网服务填写 `Providers`
   - `ollama`：`api_base_url` 常见为 `http://127.0.0.1:11434/v1`
   - `vllm`：`api_base_url` 常见为 `http://127.0.0.1:8000/v1`
3. 在 `Router.default` 指定默认模型

请勿将 `config.azure.json` 提交到仓库。

## 2. 启动 API 服务

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8001
```

OpenAPI 页面：`http://127.0.0.1:8001/docs`

## 3. 端点清单

- `GET /healthz`：健康检查
- `GET /config/runtime`：返回运行时配置路径、输出目录和可调参数清单
- `POST /analyze/match`：指标歧义匹配，返回候选列表
- `POST /analyze`：分析并生成报告 docx

## 4. 调用示例

### 4.1 健康检查

```bash
curl http://127.0.0.1:8001/healthz
```

### 4.2 歧义匹配

```bash
curl -X POST "http://127.0.0.1:8001/analyze/match" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "excel_path=/path/to/data.xlsx" \
  -d "user_prompt=分析最近一年产量趋势" \
  -d "sheet_name=Sheet1" \
  -d "use_llm_structure=true"
```

### 4.3 生成报告

```bash
curl -X POST "http://127.0.0.1:8001/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "excel_path": "/path/to/data.xlsx",
    "user_prompt": "分析最近一年产量趋势并给出建议",
    "sheet_name": "Sheet1",
    "use_llm_structure": true,
    "selected_indicator_names": ["产量"]
  }'
```
