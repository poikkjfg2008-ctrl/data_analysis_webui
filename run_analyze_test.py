from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict

import requests


def _ensure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if stream is None or not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def build_payload(args: argparse.Namespace) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "excel_path": args.excel_path,
        "user_prompt": args.user_prompt,
    }
    if args.sheet_name:
        payload["sheet_name"] = args.sheet_name
    if args.output_dir:
        payload["output_dir"] = args.output_dir
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Test /analyze API with an Excel file")
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/analyze",
        help="API endpoint URL",
    )
    parser.add_argument(
        "--excel-path",
        default="D:/codes/data_analysis/data/test.xlsx",
        help="Excel file path",
    )
    parser.add_argument(
        "--user-prompt",
        default="分析粗钢、汽车轮胎:半钢胎最近一年的趋势",
        help="Prompt for analysis（需明确指标名称，如：粗钢、汽车轮胎:半钢胎）",
    )
    parser.add_argument("--sheet-name", default=None, help="Optional sheet name")
    parser.add_argument(
        "--output-dir",
        default="D:/codes/data_analysis/data/reports",
        help="Output directory",
    )

    args = parser.parse_args()
    _ensure_utf8_stdio()
    payload = build_payload(args)

    try:
        response = requests.post(args.url, json=payload, timeout=60)
    except requests.RequestException as exc:
        print(f"请求失败: {exc}")
        print("请确认 FastAPI 服务已启动: python -m uvicorn src.main:app --reload")
        return 1

    if not response.ok:
        print(f"请求失败: HTTP {response.status_code}")
        print(response.text)
        return 1

    try:
        data = response.json()
    except ValueError:
        print("返回不是 JSON:")
        print(response.text)
        return 1

    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
