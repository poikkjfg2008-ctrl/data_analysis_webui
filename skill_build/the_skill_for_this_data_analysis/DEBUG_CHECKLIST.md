# Data Analysis Skill 调试 Checklist（项目可直接使用）

> 适用对象：`skill_build/the_skill_for_this_data_analysis`（Excel 分析并生成 `.docx` 报告）
>
> 目标：提供一套可落地的**调试清单 + 命令模板 + 日志字段 + 判定标准**，用于日常开发、联调、回归与线上故障排查。

---

## 0. 调试总原则

1. **先连通、后语义、再性能**：先确认服务活着，再确认指标匹配，再做超时/吞吐优化。
2. **每次只改一个变量**：例如只改 prompt 或只改 timeout，避免混淆结论。
3. **所有结果可复现**：记录命令、输入文件、时间窗口、输出路径与错误码。
4. **脚本优先**：优先使用项目脚本 `scripts/call_data_analysis_api.py`，降低人工调用差异。

---

## 1. 启动与环境检查（P0）

### 1.1 启动 API

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8001
```

### 1.2 健康检查

```bash
curl -sS http://127.0.0.1:8001/healthz | jq .
```

### 1.3 依赖服务检查（如 Ollama/vLLM）

```bash
curl -sS http://172.24.16.1:11434/v1/models | jq '.data | length'
```

### 判定标准

- **通过**：`/healthz` 返回 `status=ok`；LLM 端点可访问。
- **失败**：连接拒绝/超时/5xx。
- **处理建议**：
  - API 不通：先看 uvicorn 日志。
  - LLM 不通：检查模型服务进程、端口、网络路由。

---

## 2. 输入数据检查（P0）

### 2.1 Excel 可读性检查

```bash
python3 << 'PY'
import pandas as pd
p = '/absolute/path/to/data.xlsx'
xf = pd.ExcelFile(p)
print('sheets=', xf.sheet_names)
df = pd.read_excel(p, sheet_name=xf.sheet_names[0])
print('rows=', len(df))
print('cols=', list(df.columns))
PY
```

### 2.2 最小结构要求检查

- 有表头行
- 至少 1 个日期列（可被解析为时间）
- 至少 1 个数值指标列

### 判定标准

- **通过**：文件可读、sheet 正常、列名清晰。
- **失败**：加密/损坏/列名异常/无日期列。
- **处理建议**：导出为标准 xlsx；避免合并单元格与受保护 sheet。

---

## 3. 基础调用流程检查（P0）

### 3.1 推荐脚本调用（标准模板）

```bash
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --base-url http://127.0.0.1:8001 \
  --excel-path /absolute/path/to/data.xlsx \
  --user-prompt "分析最近一年产量和销量趋势，并给出建议"
```

### 3.2 指标歧义场景（手动指定）

```bash
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --base-url http://127.0.0.1:8001 \
  --excel-path /absolute/path/to/data.xlsx \
  --user-prompt "分析产量" \
  --select-indicators "半钢胎产量" "全钢胎产量"
```

### 判定标准

- **通过**：返回包含 `analyze.report_path`、`analyze.indicator_names`、`analyze.time_window`。
- **失败**：指标未匹配、时间窗无数据、接口报错。
- **处理建议**：先调用 `/analyze/match` 确认指标，再 `/analyze`。

---

## 4. 日志采集规范（P1）

> 建议每次调试都保留一份结构化日志（JSON 行或 TSV）用于复盘。

### 4.1 必记日志字段

| 字段 | 说明 | 示例 |
|---|---|---|
| trace_id | 单次请求唯一标识 | `ana_20260309_101530_001` |
| ts_start / ts_end | 开始/结束时间 | `2026-03-09T10:15:30Z` |
| excel_path | 输入文件绝对路径 | `/data/a.xlsx` |
| sheet_name | 实际分析 sheet | `Sheet1` |
| user_prompt | 用户原始提示词 | `分析最近半年销量` |
| matched_indicators | 匹配到的指标名 | `["销量","产量"]` |
| selected_indicators | 手动指定指标 | `["销量"]` |
| time_window | 解析出的时间范围 | `最近一年` |
| use_llm_structure | 是否启用结构识别 | `true` |
| timeout_sec | 调用超时参数 | `300` |
| http_status | 接口状态码 | `200` |
| elapsed_ms | 总耗时 | `18432` |
| report_path | 生成文档路径 | `/.../report_xxx.docx` |
| error_type | 错误分类 | `Timeout / MatchAmbiguous / NoData` |
| error_message | 错误摘要 | `Read timed out` |

### 4.2 调试落盘模板

```bash
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --base-url http://127.0.0.1:8001 \
  --excel-path /absolute/path/to/data.xlsx \
  --user-prompt "分析最近一年销量" \
  --quiet > run_output.json 2> run_error.log

# 返回码记录
echo $? > run_exit_code.txt
```

---

## 5. 常见故障排查清单（P1）

### 5.1 连接失败 / healthz 失败

**现象**：`Connection refused`、`timeout`。

**排查顺序**：
1. API 是否已启动（端口 8001）
2. 本机/容器网络是否可达
3. 依赖模型服务是否正常

**命令模板**：

```bash
curl -v http://127.0.0.1:8001/healthz
curl -v http://172.24.16.1:11434/v1/models
```

---

### 5.2 指标匹配歧义 / 未命中

**现象**：`产量`命中多个列或没有命中。

**处理策略**：
1. 先调用 `/analyze/match` 查看候选。
2. 让业务方确认“最终列名”。
3. 使用 `--select-indicators` 进行强约束。

**命令模板**：

```bash
curl -X POST "http://127.0.0.1:8001/analyze/match" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "excel_path=/absolute/path/to/data.xlsx" \
  -d "user_prompt=分析产量趋势" \
  -d "use_llm_structure=true"
```

---

### 5.3 超时（大文件/长时间窗口）

**现象**：请求超过默认超时。

**处理策略**：
1. 提升 `--timeout`（如 600/1200）。
2. 对标准表格关闭结构识别：`--no-use-llm-structure`。
3. 缩短时间窗口，先做小样本验证。

**命令模板**：

```bash
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --excel-path /absolute/path/to/large_data.xlsx \
  --user-prompt "分析主要指标趋势" \
  --timeout 1200 \
  --no-use-llm-structure
```

---

### 5.4 时间窗解析后无数据

**现象**：返回“time window 内无数据”。

**处理策略**：
1. 明确时间表达：`2024-01-01 至 2024-06-30`。
2. 检查日期列格式是否可解析。
3. 先不限定时间窗跑一次，确认基础数据存在。

---

## 6. 自动化回归 Checklist（P1）

### 6.1 单文件冒烟

```bash
bash skill_build/the_skill_for_this_data_analysis/tests/test_examples.sh
```

### 6.2 批量文件回归（串行）

```bash
for f in /data/reports/*.xlsx; do
  python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
    --excel-path "$f" \
    --user-prompt "分析所有指标的月度趋势" \
    --quiet > "${f}.json" 2> "${f}.err"
  echo "$f => $?"
done
```

### 6.3 并行回归（可选）

```bash
ls /data/*.xlsx | parallel -j 4 \
  python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
    --excel-path {} \
    --user-prompt "分析所有指标" \
    --quiet --timeout 300 \
    ">.{}_report.json 2>{}_errors.log"
```

### 判定标准（建议阈值）

- 成功率 ≥ **95%**
- 平均耗时（P50）≤ **60s**（按你们环境调整）
- 超时率 ≤ **3%**
- 指标匹配人工复核准确率 ≥ **90%**

---

## 7. 上线前 Gate（P0）

发布前必须满足：

- [ ] 健康检查通过（API + LLM）
- [ ] 至少 1 个真实业务文件端到端成功
- [ ] 歧义指标场景可通过 `--select-indicators` 稳定处理
- [ ] 产物路径可访问，`.docx` 可打开
- [ ] 异常日志可定位到根因（连接/匹配/超时/无数据）
- [ ] 批量回归达标（成功率、超时率、耗时）

---

## 8. 建议的优化迭代节奏（每周）

1. 汇总失败样本 Top N（按 `error_type`）
2. 对“高频歧义指标”建立同义词映射表
3. 固化 10 份黄金样例 Excel 做回归基准
4. 比较 `use_llm_structure=true/false` 的耗时与准确率
5. 每周输出一页运维简报：成功率、超时率、平均耗时、Top 错误

---

## 9. 一页版快速执行（给值班同学）

```bash
# 1) 检查服务
curl -sS http://127.0.0.1:8001/healthz | jq .

# 2) 跑一次分析
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --base-url http://127.0.0.1:8001 \
  --excel-path /absolute/path/to/data.xlsx \
  --user-prompt "分析最近一年产量和销量趋势，并给出建议" \
  --timeout 300

# 3) 失败时收集日志
python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \
  --base-url http://127.0.0.1:8001 \
  --excel-path /absolute/path/to/data.xlsx \
  --user-prompt "分析最近一年销量" \
  --quiet > run_output.json 2> run_error.log

echo $? > run_exit_code.txt
```

