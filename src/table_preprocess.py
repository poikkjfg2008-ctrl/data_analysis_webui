from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import pandas as pd


def is_null_like(value) -> bool:
    """判断一个值是否为空值/null。"""
    if pd.isna(value):
        return True
    if isinstance(value, str):
        s = value.strip().lower()
        if s in {"", "null", "none", "nan"}:
            return True
    return False


def read_table(file_path: str, sheet_name: str | None = None) -> pd.DataFrame:
    """根据文件后缀读取通用表格（csv/xlsx/xls）。"""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path, sheet_name=sheet_name)
    raise ValueError(f"Unsupported file format: {suffix}")


def parse_table_columns_from_df(df: pd.DataFrame, threshold: int = 10) -> Tuple[List[str], List[str]]:
    """按唯一值数量解析列：返回(定位列, 数值列候选)。"""
    low_cols: List[str] = []
    high_cols: List[str] = []

    for col in df.columns:
        series = df[col]
        if series.map(is_null_like).any():
            high_cols.append(str(col))
            continue

        unique_count = series.nunique(dropna=True)
        if unique_count <= threshold:
            low_cols.append(str(col))
        else:
            high_cols.append(str(col))

    return low_cols, high_cols


def parse_table_columns(file_path: str, threshold: int = 10, sheet_name: str | None = None) -> Tuple[List[str], List[str]]:
    """文件版解析接口，返回(定位列, 数值列候选)。"""
    df = read_table(file_path=file_path, sheet_name=sheet_name)
    return parse_table_columns_from_df(df=df, threshold=threshold)

