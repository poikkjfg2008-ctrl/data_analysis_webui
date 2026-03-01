# 快速开始指南

本指南帮助您在 5 分钟内启动并运行 Data Analysis WebUI 项目。

## 📋 前置条件检查

```bash
# 1. 检查 Python 版本（需要 3.9+）
python3 --version

# 2. 检查 Ollama 服务可访问性
curl http://172.24.16.1:11434/v1/models

# 3. 检查 qwen3:14b 模型已安装（在 Ollama 机器上）
ollama list | grep qwen3
```

如果以上检查都通过，继续下面的步骤。否则，请参考 [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) 的详细部署步骤。

## 🚀 快速启动（3 步）

### 步骤 1: 安装依赖

```bash
cd /home/yy/data_analysis_webui

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 步骤 2: 验证配置

配置文件 `api/config.azure.json` 已设置好您的 Ollama 服务：

```json
{
  "Providers": [{
    "name": "ollama",
    "api_base_url": "http://172.24.16.1:11434/v1",
    "models": ["qwen3:14b"]
  }],
  "Router": { "default": "ollama,qwen3:14b" }
}
```

### 步骤 3: 启动服务

```bash
# 激活虚拟环境（如果还未激活）
source venv/bin/activate

# 启动 API 服务
uvicorn src.main:app --host 0.0.0.0 --port 8001
```

服务启动后，您会看到类似以下的输出：

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001
```

## ✅ 验证安装

在另一个终端窗口中运行：

```bash
# 健康检查
curl http://127.0.0.1:8001/healthz
# 预期输出: {"status":"ok"}

# 查看配置
curl http://127.0.0.1:8001/config/runtime
```

## 🎯 第一次测试

### 1. 创建测试数据

```python
# 创建测试文件 create_test_data.py
import pandas as pd
from datetime import datetime, timedelta
import random

# 生成一年的每日数据
dates = [datetime.today() - timedelta(days=i) for i in range(365, 0, -1)]

data = {
    '日期': dates,
    '产量': [random.randint(800, 1200) for _ in range(365)],
    '销量': [random.randint(750, 1150) for _ in range(365)],
    '库存': [random.randint(200, 500) for _ in range(365)],
}

df = pd.DataFrame(data)
df.to_excel('test_data.xlsx', index=False)
print(f"✓ 测试文件已创建: test_data.xlsx ({len(df)} 行)")
```

运行：
```bash
python3 create_test_data.py
```

### 2. 运行分析

```bash
# 确保虚拟环境已激活
source venv/bin/activate

# 使用提供的脚本调用 API
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --base-url http://127.0.0.1:8001 \
  --excel-path $(pwd)/test_data.xlsx \
  --user-prompt "分析最近一年产量和销量的趋势"
```

### 3. 查看结果

成功后，脚本会输出类似以下的 JSON：

```json
{
  "healthz": {"status": "ok"},
  "match": {"status": "ok", "indicator_names": ["产量", "销量"]},
  "selected_indicator_names": ["产量", "销量"],
  "analyze": {
    "report_path": "/home/yy/data_analysis_webui/data/reports/report_20250301_143025.docx",
    "time_window": {"type": "relative", "value": "最近一年"},
    "indicator_names": ["产量", "销量"],
    "sheet_name": "Sheet1",
    "date_column": "日期"
  }
}
```

打开生成的 Word 文档查看分析报告！

## 📖 使用示例

### 示例 1: 基础趋势分析

```bash
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --base-url http://127.0.0.1:8001 \
  --excel-path /path/to/your_data.xlsx \
  --user-prompt "分析最近一个季度的销量趋势"
```

### 示例 2: 多指标对比

```bash
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --base-url http://127.0.0.1:8001 \
  --excel-path /path/to/your_data.xlsx \
  --user-prompt "分析产量和销量的相关性，给出建议"
```

### 示例 3: 精确指定指标

```bash
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --base-url http://127.0.0.1:8001 \
  --excel-path /path/to/your_data.xlsx \
  --user-prompt "分析库存情况" \
  --select-indicators "库存数量" "入库数量" "出库数量"
```

## 🌐 使用 WebUI 界面（可选）

如果需要更友好的交互界面，启动 WebUI：

```bash
# 确保虚拟环境已激活
source venv/bin/activate

# 启动 WebUI
python src/gradio_app.py

# 访问 http://localhost:5600
```

WebUI 提供：
- 文件上传界面
- 多轮对话分析
- 报告在线预览
- 综合总结生成

## 🛠️ 常用命令

### 后台运行服务

```bash
# 启动后台服务
nohup uvicorn src.main:app --host 0.0.0.0 --port 8001 > api.log 2>&1 &

# 查看日志
tail -f api.log

# 停止服务
pkill -f "uvicorn src.main:app"
```

### 检查服务状态

```bash
# 健康检查
curl http://127.0.0.1:8001/healthz

# 查看运行时配置
curl http://127.0.0.1:8001/config/runtime

# 访问 API 文档
# 浏览器打开 http://127.0.0.1:8001/docs
```

## ⚠️ 常见问题速查

| 问题 | 解决方案 |
|------|---------|
| `ModuleNotFoundError` | 确保已激活虚拟环境：`source venv/bin/activate` |
| `Connection refused` | 检查 Ollama 服务是否运行：`curl http://172.24.16.1:11434/v1/models` |
| `Address already in use` | 更换端口或终止占用进程：`lsof -i :8001` |
| `model not found` | 在 Ollama 机器上拉取模型：`ollama pull qwen3:14b` |
| 超时错误 | 增大 `api/config.azure.json` 中的 `API_TIMEOUT_MS` 值 |

## 📚 下一步

- 📖 阅读完整文档：[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- 🤖 了解 Agent 技能：[skill_build/the_skill_for_this_data_analysis/SKILL.md](skill_build/the_skill_for_this_data_analysis/SKILL.md)
- 📝 查看项目说明：[README.md](README.md)
- 🔧 二次开发指南：[docs/secondary_development.md](docs/secondary_development.md)

## 🎉 开始使用！

现在您可以：

1. ✅ 准备您的 Excel 数据文件（确保包含日期列）
2. ✅ 使用 API 脚本或 WebUI 进行分析
3. ✅ 在 `data/reports/` 目录查看生成的报告
4. ✅ 根据需要调整配置参数

**提示**: 首次使用建议先用小文件测试，确认功能正常后再处理大型数据集。

---

**需要帮助？** 请查看 [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) 的故障排查章节。
