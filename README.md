# data_analysis_webui

## 安装

1. 创建虚拟环境并激活

```bash
python -m venv venv
# Windows (PowerShell)
./venv/Scripts/Activate.ps1
# Windows (cmd)
./venv/Scripts/activate.bat
```

2. 安装依赖

```bash
pip install -r requirements.txt
```

## 启动

### 启动 Gradio WebUI

```bash
python src/gradio_app.py
```

默认监听：`http://0.0.0.0:7860`。

### （可选）启动 FastAPI

```bash
uvicorn src.main:app --reload
```

## 使用说明

1. 打开 Gradio 页面后，上传 Excel/Word/文本文件。
2. 在聊天框输入分析需求（例如：生成 2024Q4 某指标报告）。
3. 若指标有歧义，按提示选择候选指标名称。
4. 报告生成后，右侧可预览 HTML 并下载 docx。
