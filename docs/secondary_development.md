# 二次开发与模块配置指南

本文面向需要在本项目上继续开发的同学，重点包括：
- 如何接入本地 Ollama 模型。
- 各模块职责与配置点。
- 常见二开方向与改造建议。

## 1. 项目结构总览

- `src/gradio_app.py`：Gradio WebUI 入口（多轮对话、文件上传、报告预览/下载）。
- `src/main.py`：FastAPI 接口入口（`/analyze`、`/analyze/match`）。
- `src/excel_parser.py`：Excel 读取与结构识别（日期列、数值列、单位）。
- `src/llm_client.py`：统一 LLM 调用层（提示词解析、相似匹配、总结生成等）。
- `src/report_docx.py` / `src/docx_chart.py`：报告文档与图表写入。
- `src/file_ingest.py`：上传文件解析（Excel、Word、文本）。
- `src/indicator_resolver.py`：指标名到列名的解析规则（新抽取公共逻辑）。
- `src/settings.py`：配置路径与报告输出目录管理（支持环境变量覆盖）。
- `api/config.azure.json`：LLM 路由配置（本地文件，不入库）。

---

## 2. 配置机制（建议先理解）

### 2.1 LLM 配置路径

系统默认读取：
- `api/config.azure.json`

可通过环境变量覆盖：
- `DATA_ANALYSIS_CONFIG_PATH=/your/path/config.json`

### 2.2 报告输出目录

默认输出目录：
- `data/reports`

可通过环境变量覆盖：
- `DATA_ANALYSIS_OUTPUT_DIR=/your/output/dir`

> 建议在部署环境（Docker / k8s / systemd）中用环境变量注入，而不是改源码。

---

## 3. 接入本地 Ollama 模型

当前 `llm_client.py` 采用 OpenAI Responses 风格请求，最稳妥的接入方式是让 Ollama 开启 OpenAI 兼容接口。

### 3.1 启动 Ollama

```bash
ollama serve
```

确保模型已拉取：

```bash
ollama pull qwen2.5:14b
```

### 3.2 创建本地配置文件

复制示例：

```bash
cp api/config.azure.json.example api/config.azure.json
```

将内容改为（示例）：

```json
{
  "API_TIMEOUT_MS": 600000,
  "HOST": "127.0.0.1",
  "PORT": 11434,
  "Providers": [
    {
      "name": "ollama",
      "api_base_url": "http://127.0.0.1:11434/v1",
      "api_key": "ollama",
      "models": ["qwen2.5:14b"]
    }
  ],
  "Router": {
    "default": "ollama,qwen2.5:14b"
  }
}
```

> 说明：
> - `api_key` 在本地 Ollama 场景通常不会校验，但本项目请求头固定携带 `api-key`，建议填任意非空字符串（如 `ollama`）。
> - 如果你使用的网关不是 `/v1` 路径，请调整 `api_base_url`。

### 3.3 验证连通性

1) 启动 WebUI：

```bash
python src/gradio_app.py
```

2) 上传样例 Excel，输入：
- “分析最近一年 XXX 指标趋势”

若可返回指标解析和报告，说明接入成功。

### 3.4 常见问题

- **返回 404 / 接口路径错误**：检查 `api_base_url` 是否含 `/v1`。
- **响应慢**：适当增大 `API_TIMEOUT_MS`，或换更小模型。
- **JSON 解析失败**：本项目已做一定容错；若仍频繁失败，可在 `parse_prompt` 与 `match_indicators_similarity` 的系统提示词中进一步约束格式。

---

## 4. 其他模块如何配置与针对性开发

### 4.1 Excel 解析模块（`excel_parser.py`）

可改造点：
- 增强日期列识别（例如“年月周”组合字段）。
- 增强单位识别（多行表头、多层合并单元格）。
- 对行业模板做“规则优先 + LLM 回退”策略。

建议：
- 为新行业模板增加单元测试样例文件，验证 `date_column`、`numeric_columns` 与 `units`。

### 4.2 指标解析模块（`indicator_resolver.py` + `llm_client.parse_prompt`）

可改造点：
- 增加企业内部术语映射（简称、同义词）。
- 支持黑名单列（不允许被选为指标）。
- 根据业务域定制“全部指标”的范围（不是所有数值列都分析）。

建议：
- “LLM 给候选 + 本地规则最终裁决”，避免误选全量列。

### 4.3 报告模块（`report_docx.py` / `docx_chart.py`）

可改造点：
- 新增图表类型（堆叠、双轴、同比/环比专用图）。
- 增加模板化报告（不同业务线不同封面和章节）。
- 将结论段落和图表解耦，支持“只更新总结不重画图”。

建议：
- 把章节生成抽象成策略类，便于按行业切换模板。

### 4.4 WebUI 模块（`gradio_app.py`）

可改造点：
- 增加“指标多选下拉框”用于歧义确认。
- 增加“模型选择”控件（前端传 provider/model）。
- 增加“提示词模板管理”（保存企业内部模板）。

建议：
- 将 UI 事件处理进一步拆分到 service 层，降低 `gradio_app.py` 复杂度。

### 4.5 API 模块（`main.py`）

可改造点：
- 增加鉴权（Token/JWT）。
- 增加任务队列（耗时报告异步生成 + 轮询查询）。
- 增加审计日志（记录 prompt、选中指标、时间窗口）。

建议：
- 对外接口保持稳定，内部用 service 模块承载业务逻辑。

---

## 5. 推荐二开步骤（落地顺序）

1. **先固定配置**：明确用 Azure 还是 Ollama，保证 `llm_client` 稳定可用。
2. **再做 Excel 解析强化**：这一步决定后续分析正确率上限。
3. **再做指标策略**：解决业务术语映射、歧义和兜底逻辑。
4. **最后做报告与 UI 体验**：在准确性稳定后优化展示与交互。

---

## 6. 部署建议

- 使用环境变量管理配置路径和输出目录：
  - `DATA_ANALYSIS_CONFIG_PATH`
  - `DATA_ANALYSIS_OUTPUT_DIR`
- 生产环境将 `api/config.azure.json` 放到挂载卷，不进镜像层。
- 为大模型请求设置合理超时、重试与日志采样。



## 7. 工作流中断恢复与进度展示（本次优化）

在 `src/gradio_app.py` 中，已增加两项关键机制：

1. **进度增量展示（避免误读 node 序列）**
   - 使用 `last_status_snapshot` 保存上一轮状态快照。
   - 每次响应基于“前后快照差异”展示进度（如 `status` 变化、`node_sequence` 新增节点）。
   - 避免把“当前返回节点列表”误当成全流程进度。

2. **中断恢复一跳生效**
   - 当指标歧义导致中断时，保存 `pending_prompt`。
   - 用户选择候选指标后，立即用 `pending_prompt` 恢复并继续处理，而不是错误地用“选择文本”作为新分析需求。

如果你后续接入真实工作流引擎（LangGraph / 自研状态机），建议把服务端返回的状态字典直接映射到这套快照比较机制上。
