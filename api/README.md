# API 配置（仅内网 Ollama / vLLM）

本目录下的真实配置文件（含 API Key 等）已被 `.gitignore` 忽略，不会提交到 Git。

## 使用方式

克隆仓库后，根据范例文件创建本地配置：

1. 复制 `config.azure.json.example` 为 `config.azure.json`
2. 按你内网服务填写 `Providers`
   - `ollama`：`api_base_url` 通常为 `http://127.0.0.1:11434/v1`
   - `vllm`：`api_base_url` 通常为 `http://127.0.0.1:8000/v1`
3. 在 `Router.default` 指定默认模型（如 `ollama,qwen2.5:14b` 或 `vllm,Qwen/Qwen2.5-14B-Instruct`）

请勿将 `config.azure.json` 提交到仓库。
