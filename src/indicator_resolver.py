from __future__ import annotations

from typing import Dict, List, Optional, Tuple

ALL_INDICATOR_KEYWORDS = ["全部", "所有", "全部指标", "所有指标", "全部列", "所有列"]


def is_all_indicators_requested(prompt: str) -> bool:
    lower_prompt = (prompt or "").lower()
    return any(keyword in lower_prompt for keyword in ALL_INDICATOR_KEYWORDS)


def resolve_selected_metrics(
    selected_names: List[str],
    numeric_columns: List[str],
    column_display_names: Dict[str, str],
) -> List[str]:
    """解析用户手动选择的指标显示名到真实列名。"""
    normalized_columns = {c.lower().strip(): c for c in numeric_columns}
    display_to_column = {column_display_names.get(c, c): c for c in numeric_columns}

    resolved_metrics: List[str] = []
    for name in selected_names:
        key = str(name).strip()
        if key in display_to_column:
            resolved_metrics.append(display_to_column[key])
            continue
        if key.lower() in normalized_columns:
            resolved_metrics.append(normalized_columns[key.lower()])
            continue
        for column in numeric_columns:
            display = column_display_names.get(column, column)
            if key in display or key in column:
                resolved_metrics.append(column)
                break

    return list(dict.fromkeys(resolved_metrics))


def resolve_prompt_metrics(
    indicator_names: List[str],
    prompt: str,
    numeric_columns: List[str],
    column_display_names: Dict[str, str],
) -> Tuple[List[str], bool]:
    """将 LLM 返回的指标名解析为真实列名。"""
    normalized_columns = {c.lower().strip(): c for c in numeric_columns}
    all_requested = is_all_indicators_requested(prompt)

    resolved_metrics: List[str] = []
    for name in indicator_names:
        key = str(name).lower().strip()
        if key in normalized_columns:
            resolved_metrics.append(normalized_columns[key])
            continue

        for column in numeric_columns:
            if key in column.lower() and column not in resolved_metrics:
                resolved_metrics.append(column)
                break
        else:
            for column in numeric_columns:
                display = column_display_names.get(column, column)
                if key in display.lower() and column not in resolved_metrics:
                    resolved_metrics.append(column)
                    break

    if not indicator_names and all_requested:
        resolved_metrics = list(numeric_columns)

    return list(dict.fromkeys(resolved_metrics)), all_requested
