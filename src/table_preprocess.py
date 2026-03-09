from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import pandas as pd


@dataclass
class PreprocessResult:
    location_columns: List[str]
    value_columns: List[str]


def is_null_like(value) -> bool:
    """判断一个值是否为空值/null。"""
    if pd.isna(value):
        return True

    if isinstance(value, str):
        s = value.strip().lower()
        if s in {"", "null", "none", "nan"}:
            return True

    return False


def read_table(file_path: str, preferred_sheet: Optional[str] = None) -> Tuple[pd.DataFrame, str]:
    """根据文件后缀读取表格，支持 csv/xlsx/xls。"""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(path), "csv"

    if suffix in {".xlsx", ".xls"}:
        xls = pd.ExcelFile(path)
        sheet = preferred_sheet if preferred_sheet in xls.sheet_names else xls.sheet_names[0]
        return xls.parse(sheet), sheet

    raise ValueError(f"Unsupported file format: {suffix}")


def parse_table_columns_from_df(
    df: pd.DataFrame,
    threshold: int = 10,
    excluded_columns: Optional[Sequence[str]] = None,
) -> PreprocessResult:
    """按唯一值计数将列拆分为定位列/数值列。"""
    excluded = {str(c) for c in (excluded_columns or [])}
    location_cols: List[str] = []
    value_cols: List[str] = []

    for col in df.columns:
        col_name = str(col)
        if col_name in excluded:
            continue

        series = df[col]
        if series.map(is_null_like).any():
            value_cols.append(col_name)
            continue

        unique_count = series.nunique(dropna=True)
        if unique_count <= threshold:
            location_cols.append(col_name)
        else:
            value_cols.append(col_name)

    return PreprocessResult(location_columns=location_cols, value_columns=value_cols)

