from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.analysis import resolve_window
from src.excel_parser import load_excel
from src.llm_client import match_indicators_similarity, parse_prompt
from src.report_docx import build_report


def _indicator_phrases_from_prompt(user_prompt: str) -> List[str]:
    """从用户描述中提取指标短语（用于精确匹配，避免「半钢胎」匹配到「全钢胎」）。"""
    parts = re.split(r"[、，]", user_prompt)
    phrases: List[str] = []
    for p in parts:
        s = p.strip()
        if not s or len(s) < 2:
            continue
        s = re.sub(r"^分析\s*", "", s)
        s = re.sub(r"最近[一二三四五六七八九十\d]*[年周天].*$", "", s)
        s = re.sub(r"趋势.*$", "", s)
        s = s.strip()
        if s and s not in ("全部", "所有", "指标", "名称"):
            phrases.append(s)
    return phrases


def _column_matches_prompt(column_name: str, user_prompt: str) -> bool:
    """列名完整出现，或用户提到的指标短语出现在列名中，或列名某段出现在描述中。"""
    if column_name in user_prompt:
        return True
    phrases = _indicator_phrases_from_prompt(user_prompt)
    if any(phrase in column_name for phrase in phrases):
        return True
    for segment in column_name.split(":"):
        segment = segment.strip()
        if len(segment) < 2 or segment not in user_prompt:
            continue
        containing = [p for p in phrases if segment in p]
        if not containing:
            return True
        if any(p in column_name for p in containing):
            return True
    return False


class AnalyzeRequest(BaseModel):
    excel_path: str = Field(default="D:/codes/data_analysis/data/test.xlsx")
    user_prompt: str = Field(..., min_length=1)
    sheet_name: Optional[str] = None
    output_dir: str = Field(default="D:/codes/data_analysis/data/reports")
    selected_indicator_names: Optional[List[str]] = None
    use_llm_structure: bool = Field(default=True, description="用 LLM 推断 Excel 日期/数值列结构，适配任意表格式；设为 false 则使用启发式规则")


class AnalyzeResponse(BaseModel):
    report_path: str
    time_window: Dict[str, str]
    indicator_names: List[str]
    sheet_name: str
    date_column: str


class MatchCandidatesItem(BaseModel):
    display: str
    column: str


class MatchResponse(BaseModel):
    status: str  # ok | not_found | ambiguous
    indicator_names: Optional[List[str]] = None
    message: Optional[str] = None
    candidates: Optional[List[MatchCandidatesItem]] = None


app = FastAPI(title="Data Analysis Agent")

CONFIG_PATH = "D:/codes/data_analysis/api/config.azure.json"


@app.post("/analyze/match", response_model=MatchResponse)
async def analyze_match(
    excel_path: str = "D:/codes/data_analysis/data/test.xlsx",
    user_prompt: str = "",
    sheet_name: Optional[str] = None,
    use_llm_structure: bool = True,
) -> MatchResponse:
    """根据用户描述做指标相似匹配；若歧义则返回候选列表供前端展示、用户选择后再调 /analyze 并传 selected_indicator_names。"""
    if not user_prompt.strip():
        return MatchResponse(status="not_found", message="请提供分析描述")
    try:
        parsed_excel = load_excel(
            excel_path,
            sheet_name,
            config_path=CONFIG_PATH if use_llm_structure else None,
            use_llm_structure=use_llm_structure,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"读取 Excel 失败: {exc}")
    columns_with_display = [
        {"display": parsed_excel.column_display_names.get(c, c), "column": c}
        for c in parsed_excel.numeric_columns
    ]
    try:
        result = match_indicators_similarity(
            config_path=CONFIG_PATH,
            user_prompt=user_prompt,
            columns_with_display=columns_with_display,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"指标匹配失败: {exc}")
    status = (result.get("status") or "ok").lower()
    if status not in ("ok", "not_found", "ambiguous"):
        status = "ok"
    return MatchResponse(
        status=status,
        indicator_names=result.get("indicator_names"),
        message=result.get("message"),
        candidates=result.get("candidates"),
    )


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    try:
        parsed_excel = load_excel(
            request.excel_path,
            request.sheet_name,
            config_path=CONFIG_PATH if request.use_llm_structure else None,
            use_llm_structure=request.use_llm_structure,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"读取 Excel 失败: {exc}")

    df = parsed_excel.df
    date_col = parsed_excel.date_column
    if df[date_col].dropna().empty:
        raise HTTPException(status_code=400, detail="未识别到有效日期列")

    date_min = df[date_col].min()
    date_max = df[date_col].max()
    date_range = (date_min.date().isoformat(), date_max.date().isoformat())

    normalized = {c.lower().strip(): c for c in parsed_excel.numeric_columns}
    display_to_column = {
        parsed_excel.column_display_names.get(c, c): c for c in parsed_excel.numeric_columns
    }

    if request.selected_indicator_names:
        # 用户已在 /analyze/match 歧义时选择，直接使用所选显示名解析为列名
        resolved_metrics = []
        for name in request.selected_indicator_names:
            key = str(name).strip()
            if key in display_to_column:
                resolved_metrics.append(display_to_column[key])
            elif key.lower() in normalized:
                resolved_metrics.append(normalized[key.lower()])
            else:
                for c in parsed_excel.numeric_columns:
                    if key in parsed_excel.column_display_names.get(c, c) or key in c:
                        resolved_metrics.append(c)
                        break
        if not resolved_metrics:
            raise HTTPException(status_code=400, detail="所选指标未匹配到任何列")
        indicator_names = request.selected_indicator_names
        all_requested = False
        try:
            parsed_prompt = parse_prompt(
                config_path=CONFIG_PATH,
                user_prompt=request.user_prompt,
                columns=parsed_excel.numeric_columns,
                date_range=date_range,
                sheets=parsed_excel.available_sheets,
            )
        except Exception:
            parsed_prompt = {"time_window": {"type": "relative", "value": "最近一年"}}
    else:
        try:
            parsed_prompt = parse_prompt(
                config_path=CONFIG_PATH,
                user_prompt=request.user_prompt,
                columns=parsed_excel.numeric_columns,
                date_range=date_range,
                sheets=parsed_excel.available_sheets,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"解析用户需求失败: {exc}")

        indicator_names = parsed_prompt.get("indicator_names") or []
        user_prompt_lower = request.user_prompt.lower()
        all_requested = any(
            keyword in user_prompt_lower
            for keyword in ["全部", "所有", "全部指标", "所有指标", "全部列", "所有列"]
        )

        resolved_metrics = []
        for name in indicator_names:
            key = str(name).lower().strip()
            if key in normalized:
                resolved_metrics.append(normalized[key])
            else:
                for c in parsed_excel.numeric_columns:
                    if key in c.lower() and c not in resolved_metrics:
                        resolved_metrics.append(c)
                        break
                else:
                    for c in parsed_excel.numeric_columns:
                        display = parsed_excel.column_display_names.get(c, c)
                        if key in display.lower() and c not in resolved_metrics:
                            resolved_metrics.append(c)
                            break

        if not indicator_names:
            if all_requested:
                resolved_metrics = parsed_excel.numeric_columns
            else:
                def _matches(col: str) -> bool:
                    display = parsed_excel.column_display_names.get(col, col)
                    return _column_matches_prompt(display, request.user_prompt)

                mentioned = [c for c in parsed_excel.numeric_columns if _matches(c)]
                if mentioned:
                    indicator_names = [parsed_excel.column_display_names.get(c, c) for c in mentioned]
                    resolved_metrics = mentioned
                else:
                    raise HTTPException(
                        status_code=400,
                        detail="请明确指标名称，或在描述中说明'全部指标/所有指标'",
                    )

    # 仅当「用户请求的指标数 < 总列数」且「实际解析出全部列」时拒绝（防止误用全部）
    if (
        resolved_metrics
        and len(indicator_names) < len(parsed_excel.numeric_columns)
        and len(resolved_metrics) == len(parsed_excel.numeric_columns)
        and not all_requested
    ):
        raise HTTPException(
            status_code=400,
            detail="请明确指标名称，或在描述中说明'全部指标/所有指标'",
        )

    if not resolved_metrics:
        raise HTTPException(status_code=400, detail="未匹配到有效指标列")

    resolved_metrics = list(dict.fromkeys(resolved_metrics))

    time_window = parsed_prompt.get("time_window") or {"type": "relative", "value": "最近一年"}
    start, end, window_label = resolve_window(time_window, date_max)
    filtered = df[(df[date_col] >= start) & (df[date_col] <= end)].copy()

    if filtered.empty:
        raise HTTPException(status_code=400, detail="时间窗口内无数据")

    report_path = build_report(
        output_dir=request.output_dir,
        title="数据分析报告",
        date_range=window_label,
        metrics=resolved_metrics,
        df=filtered,
        date_col=date_col,
        config_path=CONFIG_PATH,
        units=parsed_excel.units,
    )

    display_names = [parsed_excel.column_display_names.get(c, c) for c in resolved_metrics]
    return AnalyzeResponse(
        report_path=report_path,
        time_window=time_window,
        indicator_names=display_names,
        sheet_name=parsed_excel.sheet_name,
        date_column=date_col,
    )
