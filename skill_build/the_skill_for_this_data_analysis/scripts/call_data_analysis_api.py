#!/usr/bin/env python3
"""调用 data_analysis_webui API 的两阶段脚本：healthz -> analyze/match -> analyze。"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import requests


def post_match(
    base_url: str,
    excel_path: str,
    user_prompt: str,
    sheet_name: str | None,
    use_llm_structure: bool,
    timeout: int,
) -> dict[str, Any]:
    data = {
        "excel_path": excel_path,
        "user_prompt": user_prompt,
        "use_llm_structure": use_llm_structure,
    }
    if sheet_name:
        data["sheet_name"] = sheet_name

    resp = requests.post(
        f"{base_url}/analyze/match",
        data=data,
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def post_analyze(
    base_url: str,
    excel_path: str,
    user_prompt: str,
    sheet_name: str | None,
    use_llm_structure: bool,
    selected_indicator_names: list[str] | None,
    timeout: int,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "excel_path": excel_path,
        "user_prompt": user_prompt,
        "use_llm_structure": use_llm_structure,
    }
    if sheet_name:
        payload["sheet_name"] = sheet_name
    if selected_indicator_names:
        payload["selected_indicator_names"] = selected_indicator_names

    resp = requests.post(
        f"{base_url}/analyze",
        json=payload,
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def healthz(base_url: str, timeout: int) -> dict[str, Any]:
    resp = requests.get(f"{base_url}/healthz", timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="调用 data_analysis_webui API")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001", help="API 基础地址")
    parser.add_argument("--excel-path", required=True, help="Excel 文件路径")
    parser.add_argument("--user-prompt", required=True, help="分析需求")
    parser.add_argument("--sheet-name", default=None, help="工作表名")
    parser.add_argument(
        "--use-llm-structure",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="是否启用 LLM 结构识别（默认启用）",
    )
    parser.add_argument(
        "--select-indicators",
        nargs="*",
        default=None,
        help="手动指定指标名列表，传入后会覆盖 match 阶段歧义候选",
    )
    parser.add_argument("--timeout", type=int, default=120, help="请求超时秒数")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output: dict[str, Any] = {}

    try:
        output["healthz"] = healthz(args.base_url, args.timeout)
        match_result = post_match(
            base_url=args.base_url,
            excel_path=args.excel_path,
            user_prompt=args.user_prompt,
            sheet_name=args.sheet_name,
            use_llm_structure=args.use_llm_structure,
            timeout=args.timeout,
        )
        output["match"] = match_result

        selected_indicator_names = args.select_indicators
        if not selected_indicator_names and match_result.get("status") == "ok":
            selected_indicator_names = match_result.get("indicator_names")

        output["selected_indicator_names"] = selected_indicator_names

        analyze_result = post_analyze(
            base_url=args.base_url,
            excel_path=args.excel_path,
            user_prompt=args.user_prompt,
            sheet_name=args.sheet_name,
            use_llm_structure=args.use_llm_structure,
            selected_indicator_names=selected_indicator_names,
            timeout=max(args.timeout, 600),
        )
        output["analyze"] = analyze_result

        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except requests.HTTPError as exc:
        err = {
            "error": "http_error",
            "status_code": exc.response.status_code if exc.response is not None else None,
            "message": str(exc),
            "response": exc.response.text if exc.response is not None else None,
        }
        print(json.dumps(err, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    except requests.RequestException as exc:
        err = {
            "error": "request_error",
            "message": str(exc),
        }
        print(json.dumps(err, ensure_ascii=False, indent=2), file=sys.stderr)
        return 3
    except Exception as exc:  # noqa: BLE001
        err = {
            "error": "unexpected_error",
            "message": str(exc),
        }
        print(json.dumps(err, ensure_ascii=False, indent=2), file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
