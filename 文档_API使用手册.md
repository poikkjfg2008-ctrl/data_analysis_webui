# 数据分析 WebUI - API 使用手册

本手册详细介绍如何使用数据分析 WebUI 的 API 接口进行数据分析和报告生成。

## 📋 目录

- [API 概述](#api-概述)
- [快速开始](#快速开始)
- [API 端点详解](#api-端点详解)
- [Python 调用示例](#python-调用示例)
- [Bash 调用示例](#bash-调用示例)
- [错误处理](#错误处理)
- [最佳实践](#最佳实践)

## 🎯 API 概述

### 核心接口

| 端点 | 方法 | 功能 | 认证 |
|------|------|------|------|
| `/healthz` | GET | 健康检查 | 无 |
| `/config/runtime` | GET | 运行时配置 | 无 |
| `/analyze/match` | POST | 指标匹配 | 无 |
| `/analyze` | POST | 执行分析 | 无 |

### 设计特点

- **RESTful 设计**：遵循 REST 架构风格
- **无状态**：每个请求独立，不依赖会话
- **JSON 响应**：统一的 JSON 格式输出
- **文件路径**：支持绝对路径的本地文件
- **内网部署**：设计用于内网，无额外认证层

## 🚀 快速开始

### 最简单的调用

```bash
# 1. 确保服务运行
curl http://127.0.0.1:8001/healthz

# 2. 生成测试数据
python3 create_test_data.py

# 3. 调用分析（使用提供脚本）
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --excel-path test_data.xlsx \
  --user-prompt "分析销量趋势"
```

### 直接使用 curl

```bash
# 健康检查
curl http://127.0.0.1:8001/healthz

# 查看配置
curl http://127.0.0.1:8001/config/runtime

# 执行分析
curl -X POST "http://127.0.0.1:8001/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "excel_path": "/path/to/data.xlsx",
    "user_prompt": "分析最近一年销量趋势",
    "use_llm_structure": true
  }'
```

## 📖 API 端点详解

### 1. GET /healthz

**功能**：检查服务健康状态

**请求参数**：无

**响应示例**：
```json
{
  "status": "ok"
}
```

**状态码**：
- `200` - 服务正常

**使用场景**：
- 服务监控
- 健康检查
- 部署验证

**调用示例**：
```bash
curl http://127.0.0.1:8001/healthz
```

### 2. GET /config/runtime

**功能**：获取运行时配置信息

**请求参数**：无

**响应示例**：
```json
{
  "config_path": "/path/to/api/config.azure.json",
  "output_dir": "/path/to/data/reports",
  "context_options": [
    {
      "key": "RAW_FILE_CONTEXT_LIMIT_CHARS",
      "description": "原始文档注入上下文的绝对字符上限（最高优先级）",
      "source": "api/config.azure.json"
    },
    {
      "key": "use_llm_structure",
      "description": "是否使用 LLM 自动识别 Excel 日期列与指标列",
      "source": "API 请求参数 /analyze"
    }
  ],
  "config_options": [
    {
      "key": "API_TIMEOUT_MS",
      "description": "调用模型服务的超时毫秒数",
      "location": "api/config.azure.json"
    },
    {
      "key": "Providers[].api_base_url",
      "description": "模型服务地址（OpenAI 兼容 /v1）",
      "location": "api/config.azure.json"
    }
  ]
}
```

**使用场景**：
- 查看当前配置
- 调试配置问题
- 运维监控

### 3. POST /analyze/match

**功能**：解析用户需求，匹配指标列

**重要**：使用 `application/x-www-form-urlencoded` 格式，**不是 JSON**！

#### 请求参数（Form Data）

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `excel_path` | string | ✅ | - | Excel 文件绝对路径 |
| `user_prompt` | string | ✅ | - | 自然语言分析需求 |
| `sheet_name` | string | ❌ | auto | 工作表名称 |
| `use_llm_structure` | boolean | ❌ | true | 是否使用 LLM 识别结构 |

#### 响应格式

**情况 1：成功匹配**

```json
{
  "status": "ok",
  "indicator_names": ["产量", "销量"],
  "message": null
}
```

**情况 2：存在歧义**

```json
{
  "status": "ambiguous",
  "indicator_names": null,
  "message": "检测到多个相似列名，请选择",
  "candidates": [
    {
      "display": "产量",
      "column": "产量"
    },
    {
      "display": "半钢胎产量",
      "column": "半钢胎产量"
    },
    {
      "display": "全钢胎产量",
      "column": "全钢胎产量"
    }
  ]
}
```

**情况 3：未找到指标**

```json
{
  "status": "not_found",
  "indicator_names": null,
  "message": "无法从描述中识别指标，请明确指标名称"
}
```

#### 调用示例

```bash
# 使用 curl
curl -X POST "http://127.0.0.1:8001/analyze/match" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "excel_path=/path/to/data.xlsx" \
  -d "user_prompt=分析最近一年产量趋势" \
  -d "use_llm_structure=true"

# 使用 Python
import requests

response = requests.post(
    "http://127.0.0.1:8001/analyze/match",
    data={
        "excel_path": "/path/to/data.xlsx",
        "user_prompt": "分析最近一年产量趋势",
        "use_llm_structure": True
    },
    timeout=60
)
result = response.json()
```

### 4. POST /analyze

**功能**：执行数据分析并生成报告

**重要**：使用 `application/json` 格式！

#### 请求参数（JSON Body）

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `excel_path` | string | ✅ | - | Excel 文件绝对路径 |
| `user_prompt` | string | ✅ | - | 自然语言分析需求 |
| `sheet_name` | string | ❌ | auto | 工作表名称 |
| `use_llm_structure` | boolean | ❌ | true | 是否使用 LLM 识别结构 |
| `selected_indicator_names` | array | ❌ | auto | 手动指定指标名称列表 |
| `output_dir` | string | ❌ | auto | 报告输出目录 |

#### 请求示例

```json
{
  "excel_path": "/path/to/data.xlsx",
  "user_prompt": "分析最近一年产量和销量的趋势，比较两者的相关性",
  "sheet_name": null,
  "use_llm_structure": true,
  "selected_indicator_names": null
}
```

#### 响应格式

**成功响应**：

```json
{
  "report_path": "/path/to/data/reports/report_20250301_143025.docx",
  "time_window": {
    "type": "relative",
    "value": "最近一年"
  },
  "indicator_names": ["产量", "销量"],
  "sheet_name": "Sheet1",
  "date_column": "日期",
  "analysis_mode": "time_series",
  "agent_message": "已完成数据分析（模式：time_series），工作表：Sheet1，指标：产量、销量，时间范围：最近一年。报告文件：/path/to/data/reports/report_20250301_143025.docx。可将该报告路径返回给用户并提示下载查看完整图表与结论。"
}
```

**错误响应**：

```json
{
  "detail": "未匹配到有效指标列"
}
```

#### 调用示例

```bash
# 使用 curl
curl -X POST "http://127.0.0.1:8001/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "excel_path": "/path/to/data.xlsx",
    "user_prompt": "分析最近一年产量和销量的趋势",
    "use_llm_structure": true
  }'

# 使用 Python
import requests

response = requests.post(
    "http://127.0.0.1:8001/analyze",
    json={
        "excel_path": "/path/to/data.xlsx",
        "user_prompt": "分析最近一年产量和销量的趋势",
        "use_llm_structure": True
    },
    timeout=600
)
result = response.json()
report_path = result["report_path"]
print(f"报告已生成：{report_path}")
```

## 🐍 Python 调用示例

### 基础示例

```python
import requests
import json

def analyze_excel(excel_path, user_prompt):
    """分析 Excel 文件并生成报告"""
    url = "http://127.0.0.1:8001/analyze"

    payload = {
        "excel_path": excel_path,
        "user_prompt": user_prompt,
        "use_llm_structure": True
    }

    response = requests.post(url, json=payload, timeout=600)
    response.raise_for_status()

    return response.json()

# 使用示例
result = analyze_excel(
    excel_path="/path/to/data.xlsx",
    user_prompt="分析最近一个季度的销量趋势"
)

print(f"报告路径: {result['report_path']}")
print(f"分析指标: {', '.join(result['indicator_names'])}")
print(f"时间窗口: {result['time_window']['value']}")
```

### 完整流程示例

```python
import requests
import json

def analyze_with_disambiguation(excel_path, user_prompt):
    """完整的分析流程：匹配 -> 歧义处理 -> 分析"""
    base_url = "http://127.0.0.1:8001"

    # 步骤 1：健康检查
    health = requests.get(f"{base_url}/healthz", timeout=10)
    health.raise_for_status()
    print("✓ 服务健康")

    # 步骤 2：指标匹配
    match_resp = requests.post(
        f"{base_url}/analyze/match",
        data={
            "excel_path": excel_path,
            "user_prompt": user_prompt,
            "use_llm_structure": True
        },
        timeout=60
    )
    match_resp.raise_for_status()
    match_result = match_resp.json()

    # 步骤 3：处理匹配结果
    status = match_result.get("status")

    if status == "ambiguous":
        # 存在歧义，需要用户选择
        candidates = match_result.get("candidates", [])
        print("检测到歧义，请选择指标：")
        for i, cand in enumerate(candidates, 1):
            print(f"{i}. {cand['display']}")

        # 假设用户选择了前两个
        selected = [cand["display"] for cand in candidates[:2]]

    elif status == "not_found":
        print("未找到匹配的指标")
        return None

    else:  # status == "ok"
        selected = match_result.get("indicator_names", [])

    print(f"✓ 指标匹配: {', '.join(selected)}")

    # 步骤 4：执行分析
    analyze_resp = requests.post(
        f"{base_url}/analyze",
        json={
            "excel_path": excel_path,
            "user_prompt": user_prompt,
            "selected_indicator_names": selected,
            "use_llm_structure": True
        },
        timeout=600
    )
    analyze_resp.raise_for_status()
    result = analyze_resp.json()

    print(f"✓ 分析完成")
    print(f"  报告: {result['report_path']}")
    print(f"  指标: {', '.join(result['indicator_names'])}")
    print(f"  时间范围: {result['time_window']['value']}")

    return result

# 使用
result = analyze_with_disambiguation(
    excel_path="/path/to/data.xlsx",
    user_prompt="分析产量和销量的相关性"
)
```

### 批量处理示例

```python
import requests
from pathlib import Path

def batch_analyze(file_pattern, prompt):
    """批量分析多个文件"""
    base_url = "http://127.0.0.1:8001"
    files = Path(".").glob(file_pattern)

    results = []

    for file in files:
        print(f"处理: {file}")

        try:
            response = requests.post(
                f"{base_url}/analyze",
                json={
                    "excel_path": str(file.absolute()),
                    "user_prompt": prompt,
                    "use_llm_structure": False  # 批量时禁用 LLM 以加速
                },
                timeout=600
            )
            response.raise_for_status()
            result = response.json()
            results.append(result)
            print(f"  ✓ 成功: {result['report_path']}")

        except Exception as e:
            print(f"  ✗ 失败: {e}")
            results.append({"error": str(e), "file": str(file)})

    return results

# 使用示例
results = batch_analyze(
    file_pattern="data/*.xlsx",
    prompt="分析所有指标的月度趋势"
)

# 输出汇总
print("\n汇总:")
for r in results:
    if "error" not in r:
        print(f"  ✓ {r['report_path']}")
```

### 带重试的示例

```python
import requests
import time

def analyze_with_retry(excel_path, user_prompt, max_retries=3):
    """带重试机制的分析"""
    base_url = "http://127.0.0.1:8001"

    for attempt in range(1, max_retries + 1):
        try:
            print(f"尝试 {attempt}/{max_retries}...")

            response = requests.post(
                f"{base_url}/analyze",
                json={
                    "excel_path": excel_path,
                    "user_prompt": user_prompt,
                    "use_llm_structure": True
                },
                timeout=600
            )
            response.raise_for_status()

            print("✓ 成功")
            return response.json()

        except requests.exceptions.Timeout:
            print(f"  超时")
            if attempt < max_retries:
                time.sleep(5)  # 等待 5 秒后重试
            else:
                raise

        except requests.exceptions.HTTPError as e:
            print(f"  HTTP 错误: {e.response.status_code}")
            if e.response.status_code >= 500 and attempt < max_retries:
                time.sleep(10)
            else:
                raise

        except Exception as e:
            print(f"  错误: {e}")
            raise

# 使用
result = analyze_with_retry(
    excel_path="/path/to/data.xlsx",
    user_prompt="分析产量趋势"
)
```

## 💻 Bash 调用示例

### 基础调用

```bash
#!/bin/bash

EXCEL_FILE="/path/to/data.xlsx"
PROMPT="分析最近一年销量趋势"
BASE_URL="http://127.0.0.1:8001"

# 调用分析接口
curl -X POST "${BASE_URL}/analyze" \
  -H "Content-Type: application/json" \
  -d "{
    \"excel_path\": \"${EXCEL_FILE}\",
    \"user_prompt\": \"${PROMPT}\",
    \"use_llm_structure\": true
  }" \
  | jq .
```

### 使用提供的脚本

```bash
# 基础用法
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --excel-path /path/to/data.xlsx \
  --user-prompt "分析销量趋势"

# 指定指标
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --excel-path /path/to/data.xlsx \
  --user-prompt "分析库存" \
  --select-indicators "库存数量" "入库数量" "出库数量"

# 安静模式（仅输出 JSON）
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --excel-path /path/to/data.xlsx \
  --user-prompt "分析产量" \
  --quiet > result.json

# 自定义超时
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --excel-path /path/to/large_file.xlsx \
  --user-prompt "分析所有指标" \
  --timeout 600
```

### 批量处理脚本

```bash
#!/bin/bash

# 批量分析脚本
BASE_URL="http://127.0.0.1:8001"
PROMPT="分析所有指标的月度趋势"
OUTPUT_DIR="batch_results"

mkdir -p "$OUTPUT_DIR"

for file in data/*.xlsx; do
    echo "处理: $file"

    python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
      --base-url "$BASE_URL" \
      --excel-path "$file" \
      --user-prompt "$PROMPT" \
      --quiet > "$OUTPUT_DIR/$(basename $file .xlsx).json" 2>&1

    if [ $? -eq 0 ]; then
        report_path=$(jq -r '.analyze.report_path' "$OUTPUT_DIR/$(basename $file .xlsx).json")
        echo "  ✓ 成功: $report_path"
    else
        echo "  ✗ 失败"
    fi
done

echo "批量处理完成，结果保存在: $OUTPUT_DIR"
```

### 健康检查脚本

```bash
#!/bin/bash

# 服务健康检查脚本

check_health() {
    local url="$1"

    response=$(curl -s -o /dev/null -w "%{http_code}" "$url/healthz")

    if [ "$response" = "200" ]; then
        echo "✓ 服务正常"
        return 0
    else
        echo "✗ 服务异常 (HTTP $response)"
        return 1
    fi
}

# 使用
if check_health "http://127.0.0.1:8001"; then
    echo "可以开始分析"
else
    echo "请先启动服务"
    exit 1
fi
```

## ⚠️ 错误处理

### HTTP 状态码

| 状态码 | 含义 | 常见原因 | 解决方案 |
|--------|------|----------|----------|
| 200 | 成功 | - | - |
| 400 | 请求错误 | 参数错误、文件不存在 | 检查请求参数 |
| 500 | 服务器错误 | Excel 解析失败、LLM 错误 | 查看详细错误信息 |

### 错误响应格式

```json
{
  "detail": "错误详细信息"
}
```

### 常见错误处理

#### 1. 文件不存在

```python
try:
    response = requests.post(url, json=payload)
    response.raise_for_status()
except requests.HTTPError as e:
    if e.response.status_code == 400:
        error = e.response.json()
        if "not found" in error.get("detail", "").lower():
            print("错误：文件不存在，请检查路径")
        else:
            print(f"错误：{error['detail']}")
    raise
```

#### 2. 超时处理

```python
try:
    response = requests.post(url, json=payload, timeout=600)
    response.raise_for_status()
except requests.exceptions.Timeout:
    print("错误：请求超时，请尝试增大超时时间或使用更小的文件")
```

#### 3. 连接错误

```python
try:
    response = requests.post(url, json=payload)
except requests.exceptions.ConnectionError:
    print("错误：无法连接到服务，请确保服务已启动")
    print("启动命令：uvicorn src.main:app --host 0.0.0.0 --port 8001")
```

## 🎯 最佳实践

### 1. 文件路径

✅ **推荐**：使用绝对路径
```python
excel_path = "/home/user/data/sales.xlsx"  # 好
```

❌ **不推荐**：使用相对路径
```python
excel_path = "./data.xlsx"  # 可能出错
excel_path = "~/data.xlsx"  # 不支持波浪号
```

### 2. 提示词编写

✅ **好的提示词**：
- "分析最近一年产量和销量的趋势，比较两者的相关性"
- "分析 2024-01 至 2024-06 库存周转情况"

❌ **不好的提示词**：
- "分析一下" （太模糊）
- "最近怎么样" （缺少时间范围）

### 3. 超时设置

```python
# 根据文件大小调整超时
file_size = os.path.getsize(excel_path) / (1024 * 1024)  # MB

if file_size < 1:
    timeout = 60
elif file_size < 10:
    timeout = 300
else:
    timeout = 600
```

### 4. 使用 LLM 结构识别

```python
# 标准格式的 Excel：禁用 LLM 以加速
payload["use_llm_structure"] = False

# 复杂/非标准格式：启用 LLM
payload["use_llm_structure"] = True
```

### 5. 错误处理

```python
# 完整的错误处理
try:
    response = requests.post(url, json=payload, timeout=600)
    response.raise_for_status()
except requests.exceptions.Timeout:
    # 处理超时
    pass
except requests.exceptions.HTTPError as e:
    # 处理 HTTP 错误
    error_detail = e.response.json().get("detail", "未知错误")
    print(f"HTTP 错误：{error_detail}")
except requests.exceptions.RequestException as e:
    # 处理其他请求错误
    print(f"请求错误：{e}")
```

### 6. 日志记录

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"开始分析: {excel_path}")
response = requests.post(url, json=payload, timeout=600)
logger.info(f"分析完成，报告: {response.json()['report_path']}")
```

## 📊 返回值处理

### 提取报告路径

```python
result = response.json()
report_path = result.get("report_path")

if report_path:
    print(f"报告已生成: {report_path}")

    # 检查文件是否存在
    import os
    if os.path.exists(report_path):
        print(f"文件大小: {os.path.getsize(report_path)} 字节")
```

### 提取分析信息

```python
result = response.json()

# 基本信息
print(f"工作表: {result['sheet_name']}")
print(f"日期列: {result['date_column']}")

# 指标信息
indicators = result['indicator_names']
print(f"分析指标: {', '.join(indicators)}")

# 时间窗口
time_window = result['time_window']
print(f"时间窗口: {time_window['value']}")
```

## 🎉 总结

本手册介绍了数据分析 WebUI API 的完整使用方法：

- ✅ 4 个核心接口
- ✅ 完整的调用示例
- ✅ 错误处理方法
- ✅ 批量处理技巧
- ✅ 最佳实践建议

掌握这些内容后，您就可以灵活地将数据分析能力集成到您的应用中了！

**更多示例请参考**：
- `skill_build/.../EXAMPLES.md` - 20+ 使用示例
- `文档_快速开始.md` - 快速入门指南
- `文档_部署指南.md` - 完整部署文档
