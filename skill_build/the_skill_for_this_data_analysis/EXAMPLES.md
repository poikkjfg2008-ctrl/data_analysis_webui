# Data Analysis Report Skill - Usage Examples

This document provides comprehensive examples for using the Data Analysis Report skill.

## Prerequisites

1. API server running: `uvicorn src.main:app --host 0.0.0.0 --port 8001`
2. Ollama/vLLM service accessible
3. Test Excel file available

## Basic Examples

### Example 1: Simple Trend Analysis

```bash
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --base-url http://127.0.0.1:8001 \
  --excel-path /path/to/sales_data.xlsx \
  --user-prompt "分析最近一个季度的销量趋势"
```

**Expected Output:**
```
📁 File: /path/to/sales_data.xlsx
📝 Prompt: 分析最近一个季度的销量趋势

💓 Checking service health...
✓ Health check passed

🔍 Matching indicators...
✓ Metrics matched: 销量

📊 Executing analysis...
✓ Analysis complete

✓ Analysis complete!

📊 Report: /home/yy/data_analysis_webui/data/reports/report_20250301_143025.docx
📈 Metrics: 销量
📅 Period: 最近一年
📁 Source: Sheet1

打开 Word 文档查看完整图表与详细分析。
```

### Example 2: Multi-Metric Comparison

```bash
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --base-url http://127.0.0.1:8001 \
  --excel-path /path/to/production_data.xlsx \
  --user-prompt "分析最近半年产量和销量的相关性，并给出建议"
```

### Example 3: Absolute Time Range

```bash
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --base-url http://127.0.0.1:8001 \
  --excel-path /path/to/financial_data.xlsx \
  --user-prompt "分析 2024-01-01 至 2024-06-30 期间的收入与支出"
```

### Example 4: Manual Metric Selection

```bash
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --base-url http://127.0.0.1:8001 \
  --excel-path /path/to/inventory_data.xlsx \
  --user-prompt "分析库存周转情况" \
  --select-indicators "库存数量" "入库数量" "出库数量"
```

### Example 5: With Specific Sheet

```bash
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --base-url http://127.0.0.1:8001 \
  --excel-path /path/to/multi_sheet_report.xlsx \
  --sheet-name "Q4 2024" \
  --user-prompt "分析本季度所有指标的表现"
```

## Advanced Examples

### Example 6: Large File with Extended Timeout

```bash
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --base-url http://127.0.0.1:8001 \
  --excel-path /path/to/large_dataset.xlsx \
  --user-prompt "分析所有指标的年度趋势" \
  --timeout 600
```

### Example 7: Batch Processing Multiple Files

```bash
#!/bin/bash

# Process multiple Excel files in a directory
for file in /data/reports/*.xlsx; do
  echo "Processing: $file"

  python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
    --base-url http://127.0.0.1:8001 \
    --excel-path "$file" \
    --user-prompt "分析所有指标的月度趋势" \
    --quiet

  if [ $? -eq 0 ]; then
    echo "✓ Success: $file"
  else
    echo "✗ Failed: $file"
  fi

  echo "---"
done
```

### Example 8: Quiet Mode for Automation

```bash
# Suppress progress messages, only output JSON on error
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --base-url http://127.0.0.1:8001 \
  --excel-path /path/to/data.xlsx \
  --user-prompt "分析产量" \
  --quiet > output.json 2> errors.log

# Check exit code
if [ $? -eq 0 ]; then
  echo "Analysis completed successfully"
  report_path=$(jq -r '.analyze.report_path' output.json)
  agent_message=$(jq -r '.analyze.agent_message' output.json)
  echo "Report saved to: $report_path"
  echo "Agent summary: $agent_message"
else
  echo "Analysis failed"
  cat errors.log
fi
```

### Example 9: Without LLM Structure Detection (Faster)

```bash
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --base-url http://127.0.0.1:8001 \
  --excel-path /path/to/standard_format.xlsx \
  --user-prompt "分析数据趋势" \
  --no-use-llm-structure
```

## Integration Examples

### Example 10: Python Integration

```python
#!/usr/bin/env python3
"""Integrate data analysis into Python workflow"""

import subprocess
import json
from pathlib import Path

def analyze_excel(excel_path: str, prompt: str) -> dict:
    """Run analysis and return result as dict"""
    cmd = [
        "python",
        "skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py",
        "--base-url", "http://127.0.0.1:8001",
        "--excel-path", excel_path,
        "--user-prompt", prompt,
        "--quiet"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)

# Usage
if __name__ == "__main__":
    result = analyze_excel(
        "/data/sales.xlsx",
        "分析最近一季度的销量趋势"
    )

    if "error" not in result:
        report_path = result["analyze"]["report_path"]
        metrics = result["analyze"]["indicator_names"]

        print(f"Analysis complete!")
        print(f"Report: {report_path}")
        print(f"Metrics: {', '.join(metrics)}")
    else:
        print(f"Error: {result['error']}")
```

### Example 11: Shell Function

```bash
#!/bin/bash
# Add to ~/.bashrc or ~/.bash_aliases

analyze_data() {
  local excel_file="$1"
  local prompt="$2"
  local base_url="${3:-http://127.0.0.1:8001}"

  python ~/data_analysis_webui/skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
    --base-url "$base_url" \
    --excel-path "$excel_file" \
    --user-prompt "$prompt" | jq -r '.analyze.report_path'
}

# Usage
report_path=$(analyze_data "/data/sales.xlsx" "分析销量")
echo "Report: $report_path"
```

### Example 12: REST API Wrapper

```bash
#!/bin/bash
# Wrapper script that exposes skill as simple REST-like command

analyze() {
  local method="$1"
  shift

  case "$method" in
    "health")
      curl -s http://127.0.0.1:8001/healthz
      ;;
    "analyze")
      local file="$1"
      local prompt="$2"
      python3 skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
        --excel-path "$file" \
        --user-prompt "$prompt" \
        --quiet
      ;;
    *)
      echo "Usage: analyze {health|analyze} [args...]"
      ;;
  esac
}

# Usage
analyze health
analyze analyze /data/sales.xlsx "分析销量"
```

## Error Handling Examples

### Example 13: Handle Ambiguous Metrics

```bash
# When match returns ambiguous status
output=$(python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --excel-path /data/production.xlsx \
  --user-prompt "分析产量" 2>&1)

# Check for ambiguity
if echo "$output" | jq -e '.match.status == "ambiguous"' > /dev/null; then
  echo "Ambiguous metrics detected. Please select from:"
  echo "$output" | jq -r '.match.candidates[].display'

  # Re-run with selection
  python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
    --excel-path /data/production.xlsx \
    --user-prompt "分析产量" \
    --select-indicators "半钢胎产量" "全钢胎产量"
fi
```

### Example 14: Retry Logic

```bash
#!/bin/bash
# Analysis with automatic retry on failure

analyze_with_retry() {
  local max_attempts=3
  local attempt=1
  local file="$1"
  local prompt="$2"

  while [ $attempt -le $max_attempts ]; do
    echo "Attempt $attempt of $max_attempts..."

    output=$(python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
      --excel-path "$file" \
      --user-prompt "$prompt" \
      --quiet 2>&1)

    if [ $? -eq 0 ]; then
      echo "Success!"
      echo "$output"
      return 0
    fi

    echo "Failed, retrying in 5 seconds..."
    sleep 5
    ((attempt++))
  done

  echo "All attempts failed"
  return 1
}

# Usage
analyze_with_retry "/data/sales.xlsx" "分析销量"
```

## Performance Tuning Examples

### Example 15: Optimize for Large Files

```bash
# For files with 100K+ rows
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --excel-path /data/large_file.xlsx \
  --user-prompt "分析主要指标趋势" \
  --no-use-llm-structure \  # Skip LLM parsing for speed
  --timeout 1200            # 20 minutes
```

### Example 16: Batch Analysis with Parallel Processing

```bash
#!/bin/bash
# Process multiple files in parallel (requires GNU parallel)

ls /data/*.xlsx | parallel -j 4 \
  python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
    --excel-path {} \
    --user-prompt "分析所有指标" \
    --quiet \
    --timeout 300 \
    ">.{}_report.json 2>{}_errors.log"
```

## Output Processing Examples

### Example 17: Extract Report Path

```bash
# Get just the report path
output=$(python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --excel-path /data/sales.xlsx \
  --user-prompt "分析销量")

report_path=$(echo "$output" | jq -r '.analyze.report_path')
echo "Report: $report_path"
```

### Example 18: Validate Analysis Completeness

```bash
#!/bin/bash
# Check if analysis completed successfully

output=$(python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --excel-path "$1" \
  --user-prompt "$2" \
  --quiet 2>&1)

# Validate structure
if echo "$output" | jq -e '
  .healthz.status == "ok" and
  .analyze != null and
  .analyze.report_path != null
' > /dev/null; then
  echo "✓ Analysis completed successfully"
  exit 0
else
  echo "✗ Analysis incomplete or failed"
  echo "$output" | jq .
  exit 1
fi
```

### Example 19: Generate Summary Report

```bash
#!/bin/bash
# Analyze multiple files and generate summary

echo "Data Analysis Summary - $(date)" > summary.txt
echo "================================" >> summary.txt
echo "" >> summary.txt

for file in /data/reports/*.xlsx; do
  filename=$(basename "$file")
  echo "Processing: $filename"

  output=$(python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
    --excel-path "$file" \
    --user-prompt "分析所有指标" \
    --quiet 2>&1)

  if [ $? -eq 0 ]; then
    report_path=$(echo "$output" | jq -r '.analyze.report_path')
    metrics=$(echo "$output" | jq -r '.analyze.indicator_names | join(", ")')

    echo "File: $filename" >> summary.txt
    echo "Metrics: $metrics" >> summary.txt
    echo "Report: $report_path" >> summary.txt
    echo "" >> summary.txt
  fi
done

echo "Summary complete: summary.txt"
```

## Test Examples

### Example 20: Quick Validation Test

```bash
#!/bin/bash
# Quick test to verify skill is working

test_file="/tmp/test_data.xlsx"

# Create test data
python3 create_test_data.py  # Assuming this script exists

# Run analysis
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --excel-path "$test_file" \
  --user-prompt "分析产量" \
  --timeout 60

# Check result
if [ $? -eq 0 ]; then
  echo "✓ Skill is working correctly"
else
  echo "✗ Skill test failed"
fi
```

## Tips and Best Practices

1. **Always use absolute paths** for Excel files
2. **Start with specific prompts** to get better metric matching
3. **Use `--quiet` mode** in scripts/automation
4. **Set appropriate timeouts** for large files (>10K rows)
5. **Consider `--no-use-llm-structure`** for standard Excel formats (faster)
6. **Use `--select-indicators`** when you know exact column names
7. **Check exit codes** in scripts (`echo $?`)
8. **Parse JSON output** with `jq` for reliable data extraction

## Troubleshooting Examples

### Diagnose Connection Issues

```bash
# Test API connectivity
curl -v http://127.0.0.1:8001/healthz

# Test Ollama connectivity
curl -v http://172.24.16.1:11434/v1/models

# Run with verbose output
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --excel-path /data/test.xlsx \
  --user-prompt "test" \
  2>&1 | tee debug.log
```

### Validate Excel File

```bash
# Check if file is valid Excel
python3 << EOF
import pandas as pd
try:
    df = pd.read_excel('/path/to/file.xlsx')
    print(f"✓ Valid Excel file")
    print(f"  Sheets: {pd.ExcelFile('/path/to/file.xlsx').sheet_names}")
    print(f"  Rows: {len(df)}")
    print(f"  Columns: {list(df.columns)}")
except Exception as e:
    print(f"✗ Invalid Excel file: {e}")
EOF
```

## Additional Resources

- Main SKILL.md: Complete skill documentation
- DEPLOYMENT_GUIDE.md: Server setup and configuration
- QUICKSTART.md: Quick start guide
- Test suite: `tests/test_examples.sh`
