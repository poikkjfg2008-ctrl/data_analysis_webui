from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import warnings

import pandas as pd


@dataclass
class ParsedExcel:
    sheet_name: str
    df: pd.DataFrame
    date_column: str
    numeric_columns: List[str]
    available_sheets: List[str]
    units: Dict[str, str]
    column_display_names: Dict[str, str] = field(default_factory=dict)


def _select_best_sheet(xls: pd.ExcelFile, preferred: Optional[str]) -> str:
    if preferred and preferred in xls.sheet_names:
        return preferred

    best_sheet = xls.sheet_names[0]
    best_rows = -1
    for name in xls.sheet_names:
        df = xls.parse(name)
        rows = len(df)
        if rows > best_rows:
            best_rows = rows
            best_sheet = name
    return best_sheet


def _detect_date_column(df: pd.DataFrame) -> Tuple[str, Dict[str, float]]:
    best_col = df.columns[0]
    best_ratio = -1.0
    ratios: Dict[str, float] = {}

    for col in df.columns:
        series = _coerce_datetime(df[col])
        ratio = series.notna().mean() if len(series) else 0.0
        ratios[str(col)] = ratio
        if ratio > best_ratio:
            best_ratio = ratio
            best_col = col

    return str(best_col), ratios


def _coerce_datetime(series: pd.Series) -> pd.Series:
    """将列尽可能稳定地转成时间，避免 pandas 在自动推断格式时反复告警。"""
    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(series, errors="coerce")

    # 对纯数字列，优先按 Excel 序列日期尝试（1899-12-30 起算）
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().mean() > 0.8:
        excel_dates = pd.to_datetime(
            numeric,
            errors="coerce",
            unit="D",
            origin="1899-12-30",
        )
        if excel_dates.notna().mean() > 0.8:
            return excel_dates

    text_series = series.astype(str).str.strip()
    candidate_formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y.%m.%d",
        "%Y-%m",
        "%Y/%m",
        "%Y%m%d",
        "%Y%m",
    ]

    merged = pd.Series([pd.NaT] * len(series), index=series.index)
    for fmt in candidate_formats:
        parsed = pd.to_datetime(text_series, format=fmt, errors="coerce")
        merged = merged.where(merged.notna(), parsed)

    best = pd.to_datetime(merged, errors="coerce")
    best_ratio = best.notna().mean() if len(best) else 0.0

    # 兜底：保持兼容性，同时屏蔽 pandas 的格式推断告警。
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="Could not infer format",
            category=UserWarning,
        )
        fallback = pd.to_datetime(text_series, errors="coerce")
    fallback_ratio = fallback.notna().mean() if len(fallback) else 0.0
    return fallback if fallback_ratio > best_ratio else best


def _normalize_column_name(name: str) -> str:
    return "".join(str(name).strip().lower().split())


def _extract_unit_from_name(name: str) -> Optional[str]:
    text = str(name)
    if not text:
        return None
    for left, right in [("(", ")"), ("（", "）")]:
        if left in text and right in text:
            start = text.rfind(left)
            end = text.rfind(right)
            if 0 <= start < end:
                unit = text[start + 1 : end].strip()
                if unit:
                    return unit
    lowered = text.lower()
    if "%" in text or "percent" in lowered or "百分比" in text:
        return "%"
    return None


def _extract_units_from_rows(
    df: pd.DataFrame,
    date_col: str,
    numeric_cols: List[str],
    units: Dict[str, str],
) -> Dict[str, str]:
    updated = dict(units)
    unit_markers = {"单位", "unit"}

    unit_rows = df[df[date_col].isna()]
    for _, row in unit_rows.iterrows():
        values = [str(v).strip().lower() for v in row.values if isinstance(v, str)]
        if not any(v in unit_markers for v in values):
            continue
        for col in numeric_cols:
            value = row.get(col)
            if isinstance(value, str):
                unit = value.strip()
                if unit:
                    updated[col] = unit
        break

    unit_col = None
    indicator_col = None
    for col in df.columns:
        normalized = _normalize_column_name(col)
        if normalized in {"单位", "unit"}:
            unit_col = col
        if normalized in {"指标", "指标名称", "indicator", "indicatorname"}:
            indicator_col = col

    if unit_col and indicator_col:
        for _, row in df[[indicator_col, unit_col]].dropna().iterrows():
            indicator = str(row[indicator_col]).strip()
            unit = str(row[unit_col]).strip()
            if not indicator or not unit:
                continue
            normalized_indicator = indicator.lower()
            for col in numeric_cols:
                if col.lower() == normalized_indicator:
                    updated[col] = unit

    return updated


def load_excel(
    path: str,
    preferred_sheet: Optional[str] = None,
    config_path: Optional[str] = None,
    use_llm_structure: bool = False,
) -> ParsedExcel:
    xls = pd.ExcelFile(path)
    sheet_name = _select_best_sheet(xls, preferred_sheet)
    df = xls.parse(sheet_name)

    date_col, ratios = _detect_date_column(df)
    date_series = _coerce_datetime(df[date_col])
    df = df.assign(**{date_col: date_series})

    numeric_cols: List[str] = []
    for col in df.columns:
        if col == date_col:
            continue
        series = pd.to_numeric(df[col], errors="coerce")
        if series.notna().mean() > 0.5:
            numeric_cols.append(str(col))
            df[col] = series

    units: Dict[str, str] = {}
    for col in numeric_cols:
        unit = _extract_unit_from_name(col)
        if unit:
            units[col] = unit

    units = _extract_units_from_rows(df, date_col, numeric_cols, units)

    column_display_names: Dict[str, str] = {}
    for i in range(len(df.columns) - 1):
        c0, c1 = str(df.columns[i]), str(df.columns[i + 1])
        if c0 == date_col or c1 == date_col or ("指标" not in c0) or (":" not in c1):
            continue
        r1 = pd.to_numeric(df[c1], errors="coerce").notna().mean()
        if r1 < 0.01:
            continue
        if c0 in numeric_cols:
            numeric_cols.remove(c0)
        if c1 not in numeric_cols:
            numeric_cols.append(c1)
            df[c1] = pd.to_numeric(df[c1], errors="coerce")
        column_display_names[c1] = c1

    if use_llm_structure and config_path:
        try:
            from src.llm_client import analyze_excel_structure

            sample_by_column = {
                str(col): df[col].head(5).tolist() for col in df.columns
            }
            llm_result = analyze_excel_structure(
                config_path=config_path,
                column_names=[str(c) for c in df.columns],
                sample_by_column=sample_by_column,
            )
            llm_date = llm_result.get("date_column")
            llm_numeric = llm_result.get("numeric_columns")
            if isinstance(llm_date, str) and llm_date in df.columns:
                date_col = llm_date
                df[date_col] = _coerce_datetime(df[date_col])
            if isinstance(llm_numeric, list) and len(llm_numeric) > 0:
                numeric_cols = []
                column_display_names = {}
                for item in llm_numeric:
                    if not isinstance(item, dict):
                        continue
                    c = item.get("column")
                    d = item.get("display_name") or c
                    if c and str(c) in df.columns:
                        numeric_cols.append(str(c))
                        column_display_names[str(c)] = str(d) if d else str(c)
                for col in numeric_cols:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                units = {}
                for c in numeric_cols:
                    u = _extract_unit_from_name(c)
                    if u:
                        units[c] = u
                units = _extract_units_from_rows(df, date_col, numeric_cols, units)
        except Exception:
            pass

    return ParsedExcel(
        sheet_name=sheet_name,
        df=df,
        date_column=str(date_col),
        numeric_columns=numeric_cols,
        available_sheets=xls.sheet_names,
        units=units,
        column_display_names=column_display_names,
    )
