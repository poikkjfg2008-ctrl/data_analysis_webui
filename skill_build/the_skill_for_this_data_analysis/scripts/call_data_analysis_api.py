#!/usr/bin/env python3
"""
Data Analysis API Caller - Call the data_analysis_webui FastAPI endpoints

This script provides a two-phase workflow:
1. Health check → 2. Match indicators → 3. Execute analysis

Outputs machine-readable JSON to stdout for programmatic use.
Status messages go to stderr for user visibility.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import requests


def log(message: str) -> None:
    """Write status message to stderr"""
    print(message, file=sys.stderr)


def post_match(
    base_url: str,
    excel_path: str,
    user_prompt: str,
    sheet_name: str | None,
    use_llm_structure: bool,
    timeout: int,
) -> dict[str, Any]:
    """Call /analyze/match endpoint to resolve indicator metrics"""
    log("🔍 Matching indicators...")

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
    """Call /analyze endpoint to generate report"""
    log("📊 Executing analysis...")

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
    """Check if API service is healthy"""
    log("💓 Checking service health...")

    resp = requests.get(f"{base_url}/healthz", timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def validate_excel_path(excel_path: str) -> None:
    """Validate that Excel file exists and has correct extension"""
    path = Path(excel_path)

    if not path.is_absolute():
        raise ValueError(f"Excel path must be absolute, got: {excel_path}")

    if not path.exists():
        raise ValueError(f"Excel file not found: {excel_path}")

    if path.suffix.lower() not in {".xlsx", ".xls"}:
        raise ValueError(f"Excel file must have .xlsx or .xls extension, got: {excel_path}")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Generate data analysis reports from Excel files using AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic analysis
  %(prog)s --excel-path /data/sales.xlsx --user-prompt "分析最近一年销量趋势"

  # Multi-metric comparison
  %(prog)s --excel-path /data/production.xlsx \\
          --user-prompt "分析产量和销量的相关性"

  # Manual metric selection
  %(prog)s --excel-path /data/warehouse.xlsx \\
          --user-prompt "分析库存周转" \\
          --select-indicators "库存数量" "入库数量" "出库数量"

  # With custom timeout
  %(prog)s --excel-path /data/large_file.xlsx \\
          --user-prompt "分析所有指标" \\
          --timeout 600

Output:
  - JSON output to stdout (for programmatic use)
  - Status messages to stderr (for user visibility)
  - Exit code 0 on success, non-zero on error
        """
    )

    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8001",
        help="API base URL (default: http://127.0.0.1:8001)"
    )

    parser.add_argument(
        "--excel-path",
        required=True,
        help="Absolute path to Excel file (.xlsx or .xls)"
    )

    parser.add_argument(
        "--user-prompt",
        required=True,
        help="Natural language analysis request (e.g., '分析最近一年销量趋势')"
    )

    parser.add_argument(
        "--sheet-name",
        default=None,
        help="Worksheet name (auto-detected if omitted)"
    )

    parser.add_argument(
        "--use-llm-structure",
        action=argparse.BooleanOptionalAction,
        default=True,
        dest="use_llm_structure",
        help="Use LLM for Excel structure detection (default: enabled)"
    )

    parser.add_argument(
        "--select-indicators",
        nargs="*",
        default=None,
        metavar="INDICATOR",
        help="Manually specify indicator names (skips auto-disambiguation)"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        metavar="SECONDS",
        help="Request timeout in seconds (default: 120, analyze phase uses max(timeout, 600))"
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress status messages to stderr"
    )

    return parser.parse_args()


def format_summary(result: dict[str, Any]) -> str:
    """Format human-readable summary from API result"""
    analyze = result.get("analyze", {})
    time_window = analyze.get("time_window", {})
    indicators = analyze.get("indicator_names", [])

    parts = [
        f"✓ Analysis complete!",
        "",
        f"📊 Report: {analyze.get('report_path', 'N/A')}",
        f"📈 Metrics: {', '.join(indicators)}",
        f"📅 Period: {time_window.get('value', 'N/A')}",
        f"📁 Source: {analyze.get('sheet_name', 'N/A')}",
    ]

    # Add time window details if available
    if "start_date" in time_window and "end_date" in time_window:
        parts.append(f"   ({time_window['start_date']} to {time_window['end_date']})")

    return "\n".join(parts)


def main() -> int:
    """Main entry point"""
    args = parse_args()

    # Override logging if quiet mode
    if args.quiet:
        global log
        log = lambda _: None  # noqa: E731

    output: dict[str, Any] = {}

    try:
        # Validate Excel file
        validate_excel_path(args.excel_path)

        log(f"📁 File: {args.excel_path}")
        log(f"📝 Prompt: {args.user_prompt}")
        log("")

        # Phase 1: Health check
        output["healthz"] = healthz(args.base_url, args.timeout)
        log("✓ Health check passed")
        log("")

        # Phase 2: Match indicators (skip if manually specified)
        selected_indicator_names = args.select_indicators

        if not selected_indicator_names:
            match_result = post_match(
                base_url=args.base_url,
                excel_path=args.excel_path,
                user_prompt=args.user_prompt,
                sheet_name=args.sheet_name,
                use_llm_structure=args.use_llm_structure,
                timeout=args.timeout,
            )
            output["match"] = match_result

            # Handle match results
            status = match_result.get("status", "ok")

            if status == "ambiguous":
                candidates = match_result.get("candidates", [])
                cand_list = [c["display"] for c in candidates]
                log(f"⚠️  Ambiguous metrics detected: {', '.join(cand_list)}")
                log(f"   Please use --select-indicators to choose from candidates")
                log("")
                # Still include in output for programmatic handling
                selected_indicator_names = None

            elif status == "not_found":
                log(f"⚠️  No indicators matched from prompt")
                log(f"   Please use --select-indicators to specify metrics manually")
                selected_indicator_names = None

            elif status == "ok":
                indicator_names = match_result.get("indicator_names", [])
                selected_indicator_names = indicator_names
                log(f"✓ Metrics matched: {', '.join(indicator_names)}")
        else:
            log(f"✓ Using manually specified metrics: {', '.join(selected_indicator_names)}")

        output["selected_indicator_names"] = selected_indicator_names
        log("")

        # Phase 3: Execute analysis
        if selected_indicator_names:
            analyze_result = post_analyze(
                base_url=args.base_url,
                excel_path=args.excel_path,
                user_prompt=args.user_prompt,
                sheet_name=args.sheet_name,
                use_llm_structure=args.use_llm_structure,
                selected_indicator_names=selected_indicator_names,
                timeout=max(args.timeout, 600),  # Use at least 10 minutes for analysis
            )
            output["analyze"] = analyze_result

            log("✓ Analysis complete")
            log("")
            log(format_summary(output))
        else:
            log("⚠️  Skipping analysis (no valid indicators)")
            output["analyze"] = None

        # Output JSON to stdout
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

        log("")
        log(f"❌ HTTP Error {exc.response.status_code if exc.response else 'Unknown'}")
        if exc.response is not None:
            try:
                error_detail = exc.response.json()
                if "detail" in error_detail:
                    log(f"   {error_detail['detail']}")
            except json.JSONDecodeError:
                log(f"   {exc.response.text[:200]}")

        return 2

    except requests.RequestException as exc:
        err = {
            "error": "request_error",
            "message": str(exc),
        }
        print(json.dumps(err, ensure_ascii=False, indent=2), file=sys.stderr)

        log("")
        log("❌ Request Error")
        log(f"   {exc}")
        log("")
        log("Possible causes:")
        log("  - API service not running")
        log("  - Network connectivity issues")
        log("  - Invalid base URL")
        log("")
        log("Try:")
        log("  1. Check if service is running: curl http://127.0.0.1:8001/healthz")
        log("  2. Start service: uvicorn src.main:app --host 0.0.0.0 --port 8001")

        return 3

    except ValueError as exc:
        err = {
            "error": "validation_error",
            "message": str(exc),
        }
        print(json.dumps(err, ensure_ascii=False, indent=2), file=sys.stderr)

        log("")
        log(f"❌ Validation Error: {exc}")

        return 4

    except Exception as exc:  # noqa: BLE001
        err = {
            "error": "unexpected_error",
            "type": type(exc).__name__,
            "message": str(exc),
        }
        print(json.dumps(err, ensure_ascii=False, indent=2), file=sys.stderr)

        log("")
        log(f"❌ Unexpected Error: {type(exc).__name__}")
        log(f"   {exc}")

        return 5


if __name__ == "__main__":
    sys.exit(main())
