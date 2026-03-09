---
name: data-analysis-report
description: Generate Excel-based data analysis reports (docx + charts) through this project’s FastAPI endpoints or helper script. Use for requests like “analyze Excel data”, “compare metrics over time”, “生成数据分析报告”, or “分析趋势并给建议”. Supports ambiguity resolution for similar indicators and Chinese/English time-window expressions.
metadata:
  author: data-analysis-webui
  version: "2.1.0"
  license: MIT
---

# Data Analysis Report (Project-Aligned Skill)

Use this skill to convert Excel data into a Word analysis report with statistics, charts, and LLM-generated insights.

## When to use

- User asks to analyze `.xlsx/.xls` business data.
- User needs trend/comparison/correlation analysis over a period.
- User wants a downloadable `.docx` report.
- User mentions ambiguous metrics (e.g., “产量” might map to multiple columns).

## Project-specific paths

From the repository root:

- API app entry: `src.main:app`
- Helper script: `skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py`
- Default API URL: `http://127.0.0.1:8001`

## Standard workflow

1. **Check service**
   - `GET /healthz`
2. **Resolve indicators (recommended)**
   - `POST /analyze/match`
3. **Run analysis**
   - `POST /analyze`
4. **Return result clearly**
   - Show report path, selected indicators, resolved time window.

## Preferred command (helper script)

```bash
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --base-url http://127.0.0.1:8001 \
  --excel-path /absolute/path/to/data.xlsx \
  --user-prompt "分析最近一年产量和销量趋势，并给出建议"
```

### Important arguments

- `--excel-path` (required, absolute path)
- `--user-prompt` (required)
- `--sheet-name` (optional)
- `--select-indicators` (optional; skips disambiguation)
- `--use-llm-structure` / `--no-use-llm-structure`
- `--timeout` (optional; increase for large files)
- `--quiet` (automation-friendly)

## Direct API usage

### 1) Match indicators

```bash
curl -X POST "http://127.0.0.1:8001/analyze/match" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "excel_path=/absolute/path/to/data.xlsx" \
  -d "user_prompt=分析最近一年产量趋势" \
  -d "use_llm_structure=true"
```

### 2) Analyze

```bash
curl -X POST "http://127.0.0.1:8001/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "excel_path": "/absolute/path/to/data.xlsx",
    "user_prompt": "分析最近一年产量和销量趋势，并给出建议",
    "use_llm_structure": true,
    "selected_indicator_names": ["产量", "销量"]
  }'
```

## Input expectations

Excel should have:

- header row
- at least one date-like column
- numeric indicator columns

Avoid merged/protected sheets when possible.

## Output expectations

Success output typically includes:

- `analyze.report_path`
- `analyze.indicator_names`
- `analyze.time_window`
- `analyze.sheet_name`

Always summarize to user as:

- Report file path
- What metrics were analyzed
- What period was used
- One-line next action (“open the docx for full charts and narrative”)

## Failure handling

- **Connection refused / healthz failed**: start API server.
- **Indicator not found / ambiguous**: ask user to confirm exact column names or pass `--select-indicators`.
- **Timeout**: increase `--timeout`; optionally disable LLM structure detection.
- **No data in time window**: ask user to adjust date range wording.

## Start/stop service (project)

```bash
# start
uvicorn src.main:app --host 0.0.0.0 --port 8001

# optional web UI mode
python src/gradio_app.py
```

## Prompting guidance

Prefer prompts that include:

- metric names (or business terms close to column names)
- explicit period (e.g., 最近一年 / 2024-01-01 至 2024-06-30)
- objective (trend / comparison / anomaly / recommendation)

## Additional examples

For batch, quiet automation, and Python integration, see:

- `skill_build/the_skill_for_this_data_analysis/EXAMPLES.md`
