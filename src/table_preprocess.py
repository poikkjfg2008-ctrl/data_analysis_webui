from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

import pandas as pd


@dataclass
class TablePreprocessResult:
    low_cardinality_columns: List[str]
    high_cardinality_columns: List[str]
    null_like_columns: List[str]


def is_null_like(value) -> bool:
    if pd.isna(value):
        return True
    if isinstance(value, str):
        s = value.strip().lower()
        if s in {"", "null", "none", "nan"}:
            return True
    return False


def read_table(file_path: str) -> pd.DataFrame:
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError(f"Unsupported file format: {suffix}")


def preprocess_table_columns(df: pd.DataFrame, threshold: int = 10) -> TablePreprocessResult:
    low_cols: List[str] = []
    high_cols: List[str] = []
    null_like_cols: List[str] = []

    for col in df.columns:
        series = df[col]
        col_name = str(col)

        if series.map(is_null_like).any():
            high_cols.append(col_name)
            null_like_cols.append(col_name)
            continue

        unique_count = series.nunique(dropna=True)
        if unique_count <= threshold:
            low_cols.append(col_name)
        else:
            high_cols.append(col_name)

    return TablePreprocessResult(
        low_cardinality_columns=low_cols,
        high_cardinality_columns=high_cols,
        null_like_columns=null_like_cols,
    )
