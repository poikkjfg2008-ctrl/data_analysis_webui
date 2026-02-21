# data_analysis_webui

## 安装与启动（推荐：使用脚本）

项目根目录下提供了 Windows 与 Linux 的一键安装、启动脚本。

### Windows

| 步骤 | 操作 |
|------|------|
| 安装 | 双击运行 `install.bat`，或在 cmd 中执行 `install.bat` |
| 启动 | 双击运行 `start.bat`，或在 cmd 中执行 `start.bat` |

安装脚本会创建虚拟环境并安装 `requirements.txt` 中的依赖；启动脚本会激活虚拟环境并启动 Gradio WebUI。

### Linux / macOS

| 步骤 | 操作 |
|------|------|
| 安装 | 在终端执行 `chmod +x install.sh && ./install.sh` |
| 启动 | 执行 `chmod +x start.sh && ./start.sh`（首次需 chmod，之后直接 `./start.sh`） |

安装脚本会创建虚拟环境（`python3 -m venv venv`）并安装依赖；启动脚本会激活虚拟环境并启动 Gradio WebUI。

---

## 手动安装与启动

### 安装

1. 创建虚拟环境并激活

```bash
python -m venv venv
# Windows (PowerShell)
./venv/Scripts/Activate.ps1
# Windows (cmd)
./venv/Scripts/activate.bat
# Linux / macOS
source venv/bin/activate
```

2. 安装依赖

```bash
pip install -r requirements.txt
```

### 启动

#### 启动 Gradio WebUI

```bash
python src/gradio_app.py
```

默认监听：`http://0.0.0.0:5600`。可用 `--port` 指定端口（如 `python src/gradio_app.py --port 5601`）；若端口被占用会自动尝试 +1。

#### （可选）启动 FastAPI

```bash
uvicorn src.main:app --reload
```

---

## API 配置

分析报告、指标解析等能力依赖 LLM（如 Azure OpenAI）。使用前需在项目根目录下配置 `api/config.azure.json`（该文件已被 git 忽略，不会提交）。

本工具已使用 **GPT-5.2-chat** 进行测试，推荐在 Azure OpenAI 中部署 **gpt-5.2-chat** 并在此配置中使用。

### 步骤

1. **创建配置文件**
   - 将 `api/config.azure.json.example` 复制为 `api/config.azure.json`。

2. **填写 LLM 信息**
   - 在 `Providers` 中填写所用供应商的 `api_base_url`、`api_key` 和 `models`。
   - 在 `Router.default` 中指定默认使用的「提供商名,模型名」，例如：`"azure,gpt-5.2-chat"`。

3. **可选参数**
   - `API_TIMEOUT_MS`：请求超时时间（毫秒），默认 600000。
   - `HOST` / `PORT`：若本地另有代理或路由会用到可改，一般保持默认即可。

### 配置示例（片段）

```json
{
  "API_TIMEOUT_MS": 600000,
  "Providers": [
    {
      "name": "azure",
      "api_base_url": "https://YOUR-REGION.openai.azure.com/openai/v1",
      "api_key": "YOUR_AZURE_OPENAI_API_KEY",
      "models": ["gpt-5.2-chat"]
    }
  ],
  "Router": { "default": "azure,gpt-5.2-chat" }
}
```

未配置或未填写有效 `api_base_url`、`api_key` 时，依赖 LLM 的功能（如智能指标解析、报告生成）将不可用；仅上传与基础解析仍可使用。更多说明见 `api/README.md`。

---

## 使用说明

1. 打开 Gradio 页面后，上传 Excel/Word/文本文件。
2. 在聊天框输入分析需求（例如：生成 2024Q4 某指标报告）。
3. 若指标有歧义，按提示选择候选指标名称。
4. 报告生成后，右侧可预览 HTML 并下载 docx。
