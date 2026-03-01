---
name: data-analysis-api-caller
description: 调用 data_analysis_webui 的 FastAPI 接口完成指标歧义匹配与数据分析报告生成。用于“大模型需要直接调用本项目 API”“根据自然语言分析需求生成报告”“先匹配指标再发起分析”的场景。
---

# Data Analysis API Caller

按以下步骤调用本项目 API，优先保证稳定与可追踪。

## 1) 准备参数

- `excel_path`：待分析 Excel 文件路径（必填）
- `user_prompt`：分析需求（必填）
- `sheet_name`：工作表名（可选）
- `use_llm_structure`：是否启用 LLM 识别 Excel 结构（默认 `true`）
- `selected_indicator_names`：指标歧义时用户选定的指标名列表（可选）

## 2) 调用顺序

1. 先调用 `GET /healthz` 确认服务可用。
2. 调用 `POST /analyze/match` 获取指标匹配结果。
3. 若返回 `ambiguous`，收集候选指标并写入 `selected_indicator_names`。
4. 调用 `POST /analyze` 生成报告。

## 3) 推荐脚本

优先使用脚本：

```bash
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --base-url http://127.0.0.1:8001 \
  --excel-path /path/to/data.xlsx \
  --user-prompt "分析最近一年产量趋势并给出建议" \
  --sheet-name Sheet1
```

脚本特性：
- 自动健康检查
- 自动执行 `match -> analyze` 两阶段流程
- 支持 `--select-indicators` 手动指定指标，覆盖歧义候选
- 统一 JSON 输出，便于上层 Agent 继续处理

## 4) 失败处理

- `healthz` 失败：先启动服务 `uvicorn src.main:app --host 0.0.0.0 --port 8001`
- `match` 返回 `not_found`：改写 `user_prompt`，明确指标关键词
- `analyze` 4xx/5xx：检查 Excel 路径、sheet 名与模型配置（`api/config.azure.json`）

## 5) 输出约定

脚本 stdout 输出 JSON：
- `healthz`：健康检查结果
- `match`：指标匹配原始响应
- `selected_indicator_names`：最终用于分析的指标
- `analyze`：分析接口返回结果（包含报告路径与时间窗口）

在对话中应同时给出：
- 报告文件路径 `report_path`
- 使用的指标列表
- 解析出的时间窗口
