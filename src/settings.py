from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_DIR = PROJECT_ROOT / "api"
DEFAULT_CONFIG_PATH = API_DIR / "config.azure.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "reports"


def get_config_path() -> str:
    """返回 LLM 配置文件路径，支持环境变量覆盖。"""
    configured = os.environ.get("DATA_ANALYSIS_CONFIG_PATH")
    return configured.strip() if configured and configured.strip() else str(DEFAULT_CONFIG_PATH)


def get_output_dir() -> str:
    """返回报告输出目录，支持环境变量覆盖。"""
    configured = os.environ.get("DATA_ANALYSIS_OUTPUT_DIR")
    return configured.strip() if configured and configured.strip() else str(DEFAULT_OUTPUT_DIR)
