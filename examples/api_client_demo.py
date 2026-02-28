from __future__ import annotations

import os
from typing import Any, Dict, List

import requests


API_BASE = os.environ.get("DATA_ANALYSIS_API_BASE", "http://127.0.0.1:8000").rstrip("/")
EXCEL_PATH = os.environ.get("DATA_ANALYSIS_EXCEL_PATH", "/path/to/your.xlsx")
USER_PROMPT = os.environ.get("DATA_ANALYSIS_USER_PROMPT", "分析轮胎外胎产量最近一年趋势")
SHEET_NAME = os.environ.get("DATA_ANALYSIS_SHEET_NAME", "Sheet1")


def _pick_selected_names(match_data: Dict[str, Any]) -> List[str]:
    if (match_data.get("status") or "").lower() != "ambiguous":
        return []
    candidates = match_data.get("candidates") or []
    if not candidates:
        return []
    # 演示逻辑：默认取第一个候选；生产环境应由用户确认
    return [candidates[0].get("display")]


def run_demo() -> None:
    health = requests.get(f"{API_BASE}/health", timeout=20)
    health.raise_for_status()
    print("health:", health.json())

    options = requests.get(f"{API_BASE}/meta/options", timeout=20)
    options.raise_for_status()
    print("meta/options keys:", list(options.json().keys()))

    match = requests.post(
        f"{API_BASE}/analyze/match",
        params={
            "excel_path": EXCEL_PATH,
            "user_prompt": USER_PROMPT,
            "sheet_name": SHEET_NAME,
            "use_llm_structure": True,
        },
        timeout=120,
    )
    match.raise_for_status()
    match_data = match.json()
    print("match:", match_data)

    payload: Dict[str, Any] = {
        "excel_path": EXCEL_PATH,
        "user_prompt": USER_PROMPT,
        "sheet_name": SHEET_NAME,
        "use_llm_structure": True,
    }

    selected = _pick_selected_names(match_data)
    if selected:
        payload["selected_indicator_names"] = selected

    analyze = requests.post(
        f"{API_BASE}/analyze",
        json=payload,
        timeout=600,
    )
    analyze.raise_for_status()
    print("analyze:", analyze.json())


if __name__ == "__main__":
    run_demo()
