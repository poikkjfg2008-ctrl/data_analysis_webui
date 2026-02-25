# API 配置

本目录下的真实配置文件（含 API Key、私钥等）已被 `.gitignore` 忽略，不会提交到 Git。

## 使用方式

克隆仓库后，根据范例文件创建本地配置：

1. **LLM 服务（Azure/OpenAI 等）**
   - 复制 `config.azure.json.example` 为 `config.azure.json`
   - 填写你的 `api_base_url`、`api_key` 和 `models`

2. **Google 服务账号（如 Vertex AI）**
   - 复制 `google.json.example` 为 `google.json`
   - 填入 GCP 项目 ID、服务账号邮箱、`private_key_id` 和 `private_key`（从 GCP 控制台下载的 JSON 密钥内容）

请勿将 `config.azure.json` 或 `google.json` 提交到仓库。

## 本地 Ollama 配置示例

如果使用本地 Ollama（OpenAI 兼容接口），可在 `config.azure.json` 中配置：

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

更多二次开发说明见 `docs/secondary_development.md`。
