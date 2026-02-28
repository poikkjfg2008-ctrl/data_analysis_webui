from __future__ import annotations

import math
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd


def _configure_plot_fonts() -> None:
    # 优先使用项目 fonts 目录：英文 Times New Roman，汉字 宋体
    _fonts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts")
    if os.path.isdir(_fonts_dir):
        for f in os.listdir(_fonts_dir):
            if f.lower().endswith((".ttf", ".otf")):
                path = os.path.join(_fonts_dir, f)
                try:
                    font_manager.fontManager.addfont(path)
                except Exception:
                    pass
    available = {font.name for font in font_manager.fontManager.ttflist}
    latin_candidates = ["Times New Roman", "DejaVu Serif"]
    cjk_candidates = ["SimSun", "宋体", "Microsoft YaHei", "SimHei"]
    font_list = []
    for name in latin_candidates:
        if name in available:
            font_list.append(name)
            break
    for name in cjk_candidates:
        if name in available:
            font_list.append(name)
            break
    if not font_list:
        font_list = ["DejaVu Sans", "SimSun", "宋体"]
    plt.rcParams["font.sans-serif"] = font_list
    plt.rcParams["axes.unicode_minus"] = False


def _parse_relative_window(text: str) -> Optional[Tuple[timedelta, str]]:
    normalized = text.strip().lower()
    if "最近一年" in text or "近一年" in text or "last year" in normalized:
        return timedelta(days=365), "最近一年"
    if "最近一周" in text or "近一周" in text or "last week" in normalized:
        return timedelta(days=7), "最近一周"
    if "最近" in text and "天" in text:
        digits = "".join(ch for ch in text if ch.isdigit())
        if digits:
            days = int(digits)
            return timedelta(days=days), f"最近{days}天"
    # 半导体烤机/电测语义：很多场景按样本批次而非自然日表达分析窗口。
    if "最近" in text and any(token in text for token in ("片", "点", "样本", "批", "wafer", "lot")):
        digits = "".join(ch for ch in text if ch.isdigit())
        if digits:
            points = int(digits)
            return timedelta(days=points), f"最近{points}个样本"
    return None


def _parse_absolute_window(text: str) -> Optional[Tuple[datetime, datetime, str]]:
    if "-" not in text:
        return None
    parts = [p.strip() for p in text.replace("至", "-").split("-") if p.strip()]
    if len(parts) < 2:
        return None
    try:
        start = datetime.fromisoformat(parts[0])
        end = datetime.fromisoformat(parts[1])
    except ValueError:
        return None
    label = f"{start.date()} 至 {end.date()}"
    return start, end, label


def resolve_window(time_window: Dict[str, str], max_date: datetime) -> Tuple[datetime, datetime, str]:
    window_type = str(time_window.get("type", "relative"))
    value = str(time_window.get("value", "最近一年"))

    if window_type == "absolute":
        parsed = _parse_absolute_window(value)
        if parsed:
            return parsed[0], parsed[1], parsed[2]

    relative = _parse_relative_window(value)
    if not relative:
        relative = (timedelta(days=365), "最近一年")
    delta, label = relative
    start = max_date - delta
    end = max_date
    return start, end, label


def compute_stats(series: pd.Series) -> Dict[str, float]:
    series = series.dropna()
    if series.empty:
        return {
            "count": 0,
            "mean": math.nan,
            "min": math.nan,
            "max": math.nan,
            "start": math.nan,
            "end": math.nan,
            "abs_change": math.nan,
            "pct_change": math.nan,
            "median": math.nan,
            "std": math.nan,
            "p5": math.nan,
            "p95": math.nan,
            "cv": math.nan,
            "outlier_ratio": math.nan,
            "drift_slope": math.nan,
        }
    start_val = series.iloc[0]
    end_val = series.iloc[-1]
    abs_change = end_val - start_val
    if start_val == 0 or pd.isna(start_val):
        pct_change = math.nan
    else:
        pct_change = abs_change / start_val

    median = float(series.median())
    std = float(series.std(ddof=1)) if len(series) > 1 else 0.0
    p5 = float(series.quantile(0.05))
    p95 = float(series.quantile(0.95))
    cv = math.nan if abs(float(series.mean())) < 1e-12 else std / float(series.mean())

    q1 = float(series.quantile(0.25))
    q3 = float(series.quantile(0.75))
    iqr = q3 - q1
    if iqr <= 0:
        outlier_ratio = 0.0
    else:
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outlier_ratio = float(((series < lower) | (series > upper)).mean())

    if len(series) > 1:
        x = pd.Series(range(len(series)), dtype="float64")
        x_mean = float(x.mean())
        y = series.astype("float64")
        y_mean = float(y.mean())
        denom = float(((x - x_mean) ** 2).sum())
        if denom == 0:
            drift_slope = 0.0
        else:
            drift_slope = float(((x - x_mean) * (y - y_mean)).sum() / denom)
    else:
        drift_slope = 0.0

    return {
        "count": int(series.count()),
        "mean": float(series.mean()),
        "min": float(series.min()),
        "max": float(series.max()),
        "start": float(start_val),
        "end": float(end_val),
        "abs_change": float(abs_change),
        "pct_change": float(pct_change) if pct_change is not math.nan else math.nan,
        "median": median,
        "std": std,
        "p5": p5,
        "p95": p95,
        "cv": float(cv) if cv is not math.nan else math.nan,
        "outlier_ratio": outlier_ratio,
        "drift_slope": drift_slope,
    }


def plot_series(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    output_path: str,
    unit: Optional[str] = None,
) -> None:
    _configure_plot_fonts()
    plt.figure(figsize=(6, 3))
    plt.plot(df[date_col], df[value_col], marker="o", linewidth=1.5)
    plt.title(value_col)
    plt.xlabel("日期")
    ylabel = f"数值 ({unit})" if unit else "数值"
    plt.ylabel(ylabel)
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
