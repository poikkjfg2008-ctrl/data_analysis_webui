from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Tuple

import pandas as pd

from docx import Document
from docx.oxml.ns import qn

from src.analysis import compute_stats
from src.docx_chart import CHART_PLACEHOLDER_PREFIX, inject_editable_charts
from src.llm_client import generate_summary, infer_metric_unit

# 统计项显示：中文 (英文)
STAT_LABELS: Dict[str, str] = {
    "count": "计数 (count)",
    "mean": "平均值 (mean)",
    "min": "最小值 (min)",
    "max": "最大值 (max)",
    "start": "期初 (start)",
    "end": "期末 (end)",
    "abs_change": "绝对变化 (abs_change)",
    "pct_change": "变化率 (pct_change)",
}

# 报告字体：英文 Times New Roman，汉字 宋体
FONT_LATIN = "Times New Roman"
FONT_EAST_ASIA = "宋体"


def _set_run_fonts(run) -> None:
    """将 run 设为西文 Times New Roman、东亚 宋体。"""
    run.font.name = FONT_LATIN
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is not None:
        rFonts.set(qn("w:eastAsia"), FONT_EAST_ASIA)


def _apply_document_fonts(document: Document) -> None:
    """对文档中所有段落和表格单元格的 run 应用中英文字体。"""
    for para in document.paragraphs:
        for run in para.runs:
            _set_run_fonts(run)
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    for run in para.runs:
                        _set_run_fonts(run)


def _format_number(value: Any) -> str:
    try:
        if value is None:
            return "-"
        if isinstance(value, float) and (value != value):
            return "-"
        return f"{value:.4f}"
    except Exception:
        return str(value)


def _sanitize_filename(text: str) -> str:
    cleaned = "".join(ch if ch not in "<>:\\/?*|\"" else "_" for ch in text)
    cleaned = cleaned.strip().replace("..", ".")
    return cleaned or "chart"


def _chart_categories_and_values(
    series_df: pd.DataFrame,
    date_col: str,
    value_col: str,
) -> Tuple[List[str], List[float]]:
    """根据时间跨度决定横轴按「月」或「日」：约一年按月，约一月按日。"""
    if series_df.empty:
        return [], []
    df = series_df[[date_col, value_col]].dropna()
    if df.empty:
        return [], []
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col])
    if df.empty:
        return [], []
    span_days = (df[date_col].max() - df[date_col].min()).days
    if span_days > 60:
        df["_month"] = df[date_col].dt.to_period("M").astype(str)
        agg = df.groupby("_month", as_index=False).agg({value_col: "mean"})
        categories = agg["_month"].tolist()
        values = agg[value_col].tolist()
    else:
        df = df.sort_values(date_col)
        categories = df[date_col].dt.strftime("%m-%d").tolist()
        values = df[value_col].tolist()
    return categories, values


def build_report(
    output_dir: str,
    title: str,
    date_range: str,
    metrics: List[str],
    df,
    date_col: str,
    config_path: str,
    units: Dict[str, str],
) -> str:
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_{timestamp}.docx"
    output_path = os.path.join(output_dir, filename)

    document = Document()
    chart_data: list = []
    document.add_heading(title, level=1)
    document.add_paragraph(f"日期范围: {date_range}")
    document.add_paragraph(f"指标数量: {len(metrics)}")

    for chart_idx, metric in enumerate(metrics):
        document.add_heading(metric, level=2)
        series_df = df[[date_col, metric]].dropna()
        stats = compute_stats(series_df[metric])

        table = document.add_table(rows=1, cols=2)
        table.style = "Light Grid"
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = "统计项"
        hdr_cells[1].text = "值"
        for key, value in stats.items():
            row_cells = table.add_row().cells
            row_cells[0].text = STAT_LABELS.get(key, f"{key} ({key})")
            row_cells[1].text = _format_number(value)

        # 可编辑图表占位符；横轴按时间跨度：约一年按月、约一月按日；纵轴单位由 LLM 综合指标名与 Excel 单位自行判断
        document.add_paragraph(f"{CHART_PLACEHOLDER_PREFIX}{chart_idx}")
        categories, vals = _chart_categories_and_values(series_df, date_col, metric)
        excel_unit = units.get(metric) or None
        try:
            unit = infer_metric_unit(config_path, str(metric), excel_unit=excel_unit)
        except Exception:
            unit = excel_unit or ""
        chart_data.append((categories, vals, str(metric), unit or None))

        try:
            summary = generate_summary(config_path, metric, stats, date_range)
            document.add_paragraph(summary)
        except Exception as exc:
            document.add_paragraph(f"结论生成失败: {exc}")

    _apply_document_fonts(document)
    document.save(output_path)
    if chart_data:
        try:
            inject_editable_charts(output_path, chart_data)
        except Exception:
            pass
    return output_path
