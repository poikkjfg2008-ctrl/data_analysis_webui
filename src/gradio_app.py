from __future__ import annotations

import argparse
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Gradio Chatbot 当前版本在 postprocess 中要求每条消息为 {role, content} 字典
ChatHistory = List[Dict[str, Any]]

# 确保项目根目录在 path 中，便于以 python src/gradio_app.py 方式运行
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import gradio as gr
import mammoth
import requests

from src.analysis import resolve_window
from src.excel_parser import load_excel
from src.file_ingest import parse_uploads
from src.indicator_resolver import resolve_prompt_metrics, resolve_selected_metrics
from src.llm_client import (
    generate_conversation_summary,
    match_indicators_similarity,
    parse_prompt,
    revise_summary,
)
from src.docx_chart import inject_editable_charts
from src.report_docx import (
    append_report_section,
    append_summary_section,
    build_report,
    extract_report_text_summary,
    replace_summary_section,
)
from src.settings import get_config_path, get_output_dir

CONFIG_PATH = get_config_path()
DEFAULT_OUTPUT_DIR = get_output_dir()
# 多轮对话共用的报告文件路径，不依赖 state 传递，确保始终追加到同一 docx
SESSION_REPORT_PATH = os.path.join(DEFAULT_OUTPUT_DIR, "session_report.docx")

# 默认综合总结提示词：展示在提示词框中，并根据历史对话自动拼接「对话记录」
DEFAULT_SUMMARY_PROMPT = (
    "请根据以下对话记录生成综合总结：概括各轮分析的时间范围、指标与主要结论，"
    "并给出整体性的结论与建议。输出纯文本、分段清晰、2–5 段、中文。"
)


def _build_summary_prompt_from_history(hist: ChatHistory) -> str:
    """根据当前对话历史拼出「默认提示词 + 对话记录」，用于提示词框的自动更新。"""
    conversation_text = "\n\n".join(
        f"{'用户' if m.get('role') == 'user' else '助手'}: {m.get('content', '')}"
        for m in hist
    )
    if not conversation_text.strip():
        return DEFAULT_SUMMARY_PROMPT
    return DEFAULT_SUMMARY_PROMPT + "\n\n对话记录：\n" + conversation_text


@dataclass
class SessionState:
    excel_path: Optional[str] = None
    parsed_excel = None
    pending_candidates: Optional[List[Dict[str, str]]] = None
    pending_prompt: Optional[str] = None
    pending_time_window: Optional[Dict[str, str]] = None
    selected_indicators: Optional[List[str]] = None
    context_text: str = ""
    # 多轮对话共用的报告：路径与累计图表数据，用于追加到同一 docx
    session_report_path: Optional[str] = None
    session_chart_data: Optional[List] = None
    # 当前综合总结正文，用于多轮「修改总结」时传入 LLM
    session_summary_text: Optional[str] = None


def _update_state_with_uploads(state: SessionState, uploads) -> SessionState:
    excel_path, context_text = parse_uploads(uploads)
    if excel_path:
        state.excel_path = excel_path
        state.parsed_excel = None
    if context_text:
        state.context_text = context_text
    return state


def _load_parsed_excel(state: SessionState, sheet_name: Optional[str], use_llm: bool):
    if not state.excel_path:
        raise ValueError("请先上传 Excel 文件")
    if state.parsed_excel is None or sheet_name:
        state.parsed_excel = load_excel(
            state.excel_path,
            sheet_name,
            config_path=CONFIG_PATH if use_llm else None,
            use_llm_structure=use_llm,
        )
    return state.parsed_excel


def _combine_prompt(prompt: str, context_text: str) -> str:
    prompt = (prompt or "").strip()
    if context_text:
        return f"{prompt}\n\n补充资料:\n{context_text}" if prompt else context_text
    return prompt


def _resolve_time_window(
    prompt: str,
    parsed_excel,
    time_window_override: Optional[str],
    sheet_override: Optional[str],
) -> Tuple[Dict[str, str], Optional[str]]:
    date_col = parsed_excel.date_column
    df = parsed_excel.df
    date_min = df[date_col].min()
    date_max = df[date_col].max()
    date_range = (date_min.date().isoformat(), date_max.date().isoformat())

    if time_window_override:
        time_window = {"type": "absolute", "value": time_window_override}
        return time_window, sheet_override

    parsed_prompt = parse_prompt(
        config_path=CONFIG_PATH,
        user_prompt=prompt,
        columns=parsed_excel.numeric_columns,
        date_range=date_range,
        sheets=parsed_excel.available_sheets,
    )
    return parsed_prompt.get("time_window") or {"type": "relative", "value": "最近一年"}, parsed_prompt.get("sheet_name")


def _resolve_indicators(
    prompt: str,
    parsed_excel,
    selected_names: Optional[List[str]],
) -> Tuple[List[str], List[str], bool]:
    if selected_names:
        resolved_metrics = resolve_selected_metrics(
            selected_names=selected_names,
            numeric_columns=parsed_excel.numeric_columns,
            column_display_names=parsed_excel.column_display_names,
        )
        if not resolved_metrics:
            raise ValueError("所选指标未匹配到任何列")
        return selected_names, resolved_metrics, False

    parsed_prompt = parse_prompt(
        config_path=CONFIG_PATH,
        user_prompt=prompt,
        columns=parsed_excel.numeric_columns,
        date_range=(
            parsed_excel.df[parsed_excel.date_column].min().date().isoformat(),
            parsed_excel.df[parsed_excel.date_column].max().date().isoformat(),
        ),
        sheets=parsed_excel.available_sheets,
    )
    indicator_names = parsed_prompt.get("indicator_names") or []
    resolved_metrics, all_requested = resolve_prompt_metrics(
        indicator_names=indicator_names,
        prompt=prompt,
        numeric_columns=parsed_excel.numeric_columns,
        column_display_names=parsed_excel.column_display_names,
    )

    if not indicator_names:
        if all_requested:
            indicator_names = [parsed_excel.column_display_names.get(c, c) for c in resolved_metrics]
        else:
            raise ValueError("请明确指标名称，或在描述中说明'全部指标/所有指标'")

    if (
        resolved_metrics
        and len(indicator_names) < len(parsed_excel.numeric_columns)
        and len(resolved_metrics) == len(parsed_excel.numeric_columns)
        and not all_requested
    ):
        raise ValueError("请明确指标名称，或在描述中说明'全部指标/所有指标'")

    if not resolved_metrics:
        raise ValueError("未匹配到有效指标列")

    return indicator_names, resolved_metrics, all_requested


def _ensure_candidates(prompt: str, parsed_excel) -> Optional[List[Dict[str, str]]]:
    columns_with_display = [
        {"display": parsed_excel.column_display_names.get(c, c), "column": c}
        for c in parsed_excel.numeric_columns
    ]
    result = match_indicators_similarity(
        config_path=CONFIG_PATH,
        user_prompt=prompt,
        columns_with_display=columns_with_display,
    )
    status = (result.get("status") or "ok").lower()
    if status == "ambiguous":
        return result.get("candidates") or []
    return None


def _render_report(report_path: str) -> str:
    with open(report_path, "rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)
    html = result.value or ""
    if result.messages:
        messages = "\n".join(str(m) for m in result.messages)
        html += f"<pre>转换提示:\n{messages}</pre>"
    return html


def _wrap_report_preview(html: str) -> str:
    """将报告 HTML 包在固定高度、可独立滚动的容器内，避免整页无限下移。"""
    if not (html or "").strip():
        return ""
    return (
        '<div class="report-preview-scroll" style="'
        "max-height: 70vh; overflow-y: auto; overflow-x: hidden; "
        "border: 1px solid var(--border-color, #e0e0e0); border-radius: 6px; padding: 12px;"
        '">'
        + (html or "")
        + "</div>"
    )


def _build_report_from_state(
    state: SessionState,
    prompt: str,
    sheet_name: Optional[str],
    time_window_override: Optional[str],
    use_llm_structure: bool,
    round_index: int,
    is_first_round: bool,
) -> Tuple[str, str, List[str], List, bool]:
    """生成或追加报告。使用固定 SESSION_REPORT_PATH，不依赖 state 传路径，避免只导出最后一轮。
    返回 (report_path, window_label, display_names, chart_data, is_append)。"""
    parsed_excel = _load_parsed_excel(state, sheet_name, use_llm_structure)
    time_window, sheet_override = _resolve_time_window(
        prompt,
        parsed_excel,
        time_window_override,
        sheet_name,
    )
    if sheet_override and sheet_override != parsed_excel.sheet_name:
        parsed_excel = load_excel(
            state.excel_path,
            sheet_override,
            config_path=CONFIG_PATH if use_llm_structure else None,
            use_llm_structure=use_llm_structure,
        )
        state.parsed_excel = parsed_excel

    indicator_names, resolved_metrics, _ = _resolve_indicators(
        prompt,
        parsed_excel,
        state.selected_indicators,
    )

    date_col = parsed_excel.date_column
    df = parsed_excel.df
    date_max = df[date_col].max()
    start, end, window_label = resolve_window(time_window, date_max)
    filtered = df[(df[date_col] >= start) & (df[date_col] <= end)].copy()
    if filtered.empty:
        raise ValueError("时间窗口内无数据")

    display_names = [parsed_excel.column_display_names.get(c, c) for c in resolved_metrics]
    report_path = SESSION_REPORT_PATH

    if is_first_round:
        _, chart_data = build_report(
            output_dir=DEFAULT_OUTPUT_DIR,
            title="数据分析报告",
            date_range=window_label,
            metrics=resolved_metrics,
            df=filtered,
            date_col=date_col,
            config_path=CONFIG_PATH,
            units=parsed_excel.units,
            output_path=report_path,
        )
        return report_path, window_label, display_names, chart_data, False

    chart_start = len(state.session_chart_data or [])
    section_title = f"第{round_index}轮分析 · {window_label}"
    new_chart_data = append_report_section(
        report_path,
        section_title=section_title,
        date_range=window_label,
        metrics=resolved_metrics,
        df=filtered,
        date_col=date_col,
        config_path=CONFIG_PATH,
        units=parsed_excel.units,
        chart_start_index=chart_start,
    )
    return report_path, window_label, display_names, new_chart_data, True


def _normalize_chat_history(history: Any) -> ChatHistory:
    """将 Gradio 传入的对话历史统一为 [{role, content}, ...] 格式。"""
    if not history:
        return []
    if isinstance(history[0], dict) and "role" in history[0]:
        return list(history)
    result: ChatHistory = []
    for pair in history:
        if isinstance(pair, (list, tuple)) and len(pair) >= 2:
            result.append({"role": "user", "content": str(pair[0])})
            result.append({"role": "assistant", "content": str(pair[1])})
    return result


def _append_turn(history: ChatHistory, user_msg: str, assistant_msg: str) -> ChatHistory:
    """在历史后追加一轮对话，返回新列表（符合 Gradio role/content 格式）。"""
    out = list(history)
    out.append({"role": "user", "content": user_msg})
    out.append({"role": "assistant", "content": assistant_msg})
    return out


def handle_message(
    message: str,
    history: Any,
    uploads,
    state: SessionState,
    sheet_name: Optional[str],
    time_window_override: Optional[str],
    use_llm_structure: bool,
    use_message_for_summary_revision: bool,
) -> Tuple[ChatHistory, SessionState, str, Optional[str], Any]:
    state = _update_state_with_uploads(state, uploads)
    combined_prompt = _combine_prompt(message, state.context_text)
    hist = _normalize_chat_history(history)

    def _box_from_hist(new_hist: ChatHistory):
        return gr.update(value=_build_summary_prompt_from_history(new_hist))

    # 勾选「用于修改总结」且已有总结时：本条消息作为修改意见，多轮修订总结并回写到提示词框
    if use_message_for_summary_revision and (state.session_summary_text or "").strip() and combined_prompt:
        if not os.path.isfile(SESSION_REPORT_PATH):
            new_hist = _append_turn(hist, message, "当前尚无报告文档，无法修改总结。请先生成报告与综合总结。")
            return new_hist, state, "", None, _box_from_hist(new_hist)
        try:
            revised = revise_summary(
                CONFIG_PATH,
                state.session_summary_text,
                combined_prompt,
            )
        except requests.exceptions.Timeout:
            new_hist = _append_turn(hist, message, "请求 AI 服务超时，请稍后重试。")
            return new_hist, state, "", SESSION_REPORT_PATH, _box_from_hist(new_hist)
        except Exception as exc:
            new_hist = _append_turn(hist, message, f"修改总结失败: {exc}")
            return new_hist, state, "", SESSION_REPORT_PATH, _box_from_hist(new_hist)
        try:
            replace_summary_section(SESSION_REPORT_PATH, "综合总结", revised)
        except Exception as exc:
            new_hist = _append_turn(hist, message, f"总结已修订但写入报告失败: {exc}")
            return new_hist, state, "", SESSION_REPORT_PATH, _box_from_hist(new_hist)
        state.session_summary_text = revised
        html = _render_report(SESSION_REPORT_PATH)
        reply = "已根据您的意见更新综合总结，并已写回报告。请查看右侧报告预览。"
        new_hist = _append_turn(hist, message, reply)
        return new_hist, state, _wrap_report_preview(html), SESSION_REPORT_PATH, _box_from_hist(new_hist)

    if not combined_prompt:
        new_hist = _append_turn(hist, message, "请先输入分析需求。")
        return new_hist, state, "", None, _box_from_hist(new_hist)

    if not state.excel_path:
        new_hist = _append_turn(hist, message, "请先上传 Excel 文件。")
        return new_hist, state, "", None, _box_from_hist(new_hist)

    try:
        parsed_excel = _load_parsed_excel(state, sheet_name, use_llm_structure)
    except Exception as exc:
        new_hist = _append_turn(hist, message, f"无法读取 Excel: {exc}")
        return new_hist, state, "", None, _box_from_hist(new_hist)

    if state.pending_candidates:
        chosen = [c.strip() for c in message.split(",") if c.strip()]
        if not chosen:
            new_hist = _append_turn(hist, message, "请从候选指标中选择后再发送，例如: 指标A, 指标B")
            return new_hist, state, "", None, _box_from_hist(new_hist)
        state.selected_indicators = chosen
        state.pending_candidates = None
    else:
        try:
            candidates = _ensure_candidates(combined_prompt, parsed_excel)
        except requests.exceptions.Timeout:
            new_hist = _append_turn(hist, message, "请求 AI 服务超时，请稍后重试。")
            return new_hist, state, "", None, _box_from_hist(new_hist)
        except Exception as exc:
            new_hist = _append_turn(hist, message, f"指标匹配失败: {exc}")
            return new_hist, state, "", None, _box_from_hist(new_hist)
        if candidates:
            state.pending_candidates = candidates
            state.pending_prompt = combined_prompt
            options = ", ".join(c["display"] for c in candidates)
            new_hist = _append_turn(hist, message, f"指标存在歧义，请从以下候选中选择并回复: {options}")
            return new_hist, state, "", None, _box_from_hist(new_hist)

    round_index = len(hist) // 2 + 1
    is_first_round = len(hist) == 0
    try:
        report_path, window_label, display_names, chart_data, is_append = _build_report_from_state(
            state,
            combined_prompt,
            sheet_name,
            time_window_override,
            use_llm_structure,
            round_index,
            is_first_round,
        )
    except requests.exceptions.Timeout:
        new_hist = _append_turn(hist, message, "请求 AI 服务超时，请稍后重试。")
        return new_hist, state, "", None, _box_from_hist(new_hist)
    except Exception as exc:
        new_hist = _append_turn(hist, message, f"生成报告失败: {exc}")
        return new_hist, state, "", None, _box_from_hist(new_hist)

    if is_append:
        state.session_chart_data = (state.session_chart_data or []) + list(chart_data)
        try:
            inject_editable_charts(SESSION_REPORT_PATH, state.session_chart_data)
        except Exception:
            pass
    else:
        state.session_report_path = report_path
        state.session_chart_data = list(chart_data)

    html = _render_report(report_path)
    reply = f"已生成报告（已叠加到同一文档）。时间范围: {window_label}，指标: {', '.join(display_names)}"
    new_hist = _append_turn(hist, message, reply)
    return new_hist, state, _wrap_report_preview(html), report_path, _box_from_hist(new_hist)


def handle_generate_summary(
    history: Any,
    state: SessionState,
    summary_prompt_value: str,
) -> Tuple[ChatHistory, SessionState, str, Optional[str], Any]:
    """根据历史对话生成综合总结；提示词框内容可作为自定义提示，生成后框内展示总结正文供编辑与多轮修改。"""
    hist = _normalize_chat_history(history)

    def _box_unchanged():
        return gr.update()

    if len(hist) < 2:
        msg = "请先进行至少一轮分析对话后再点击「生成综合总结」。"
        return _append_turn(hist, "【生成综合总结】", msg), state, "", state.session_report_path or None, _box_unchanged()
    if not os.path.isfile(SESSION_REPORT_PATH):
        msg = "当前尚无报告文档，请先完成至少一轮分析生成报告后再生成综合总结。"
        return _append_turn(hist, "【生成综合总结】", msg), state, "", None, _box_unchanged()

    conversation_text = "\n\n".join(
        f"{'用户' if m.get('role') == 'user' else '助手'}: {m.get('content', '')}"
        for m in hist
    )
    user_prompt_override = (summary_prompt_value or "").strip() or None
    report_content = extract_report_text_summary(SESSION_REPORT_PATH)
    try:
        summary = generate_conversation_summary(
            CONFIG_PATH,
            conversation_text,
            user_prompt_override=user_prompt_override,
            report_content=report_content or None,
        )
    except requests.exceptions.Timeout:
        msg = "请求 AI 服务超时，请稍后重试。"
        return _append_turn(hist, "【生成综合总结】", msg), state, "", SESSION_REPORT_PATH, _box_unchanged()
    except Exception as exc:
        msg = f"生成综合总结失败: {exc}"
        return _append_turn(hist, "【生成综合总结】", msg), state, "", SESSION_REPORT_PATH, _box_unchanged()

    try:
        append_summary_section(SESSION_REPORT_PATH, "综合总结", summary)
    except Exception as exc:
        msg = f"综合总结已生成但写入报告失败: {exc}"
        new_hist = _append_turn(hist, "【生成综合总结】", msg)
        return new_hist, state, "", SESSION_REPORT_PATH, gr.update(value=_build_summary_prompt_from_history(new_hist))

    state.session_summary_text = summary
    html = _render_report(SESSION_REPORT_PATH)
    reply = "已生成综合总结并已追加到报告末尾。请查看右侧报告预览；可继续编辑上方提示词后再次生成，或勾选「将本条消息用于修改总结」在对话中多轮修改。"
    new_hist = _append_turn(hist, "【生成综合总结】", reply)
    return new_hist, state, _wrap_report_preview(html), SESSION_REPORT_PATH, gr.update(value=_build_summary_prompt_from_history(new_hist))


# 左侧对话区单滚动条、右侧报告预览独立滚动，避免双滚动条与整页无限下移
_UI_CSS = """
#conversation-chatbot { max-height: 55vh; overflow-y: auto !important; overflow-x: hidden; }
#conversation-chatbot .message { overflow-wrap: break-word; }
"""


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="数据分析 WebUI", css=_UI_CSS) as demo:
        gr.Markdown("# 数据分析 WebUI\n上传 Excel/Word/文本，输入分析需求并生成报告。")
        state = gr.State(SessionState())

        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(label="对话", elem_id="conversation-chatbot")
                message = gr.Textbox(label="输入", lines=3, placeholder="例如：分析 2024Q4 产量趋势")
                uploads = gr.Files(label="上传文件", file_types=[".xlsx", ".xls", ".docx", ".txt"],
                                    file_count="multiple")
                sheet_name = gr.Textbox(label="Sheet 名称 (可选)")
                time_window = gr.Textbox(label="时间窗口 (可选，YYYY-MM-DD 至 YYYY-MM-DD)")
                use_llm_structure = gr.Checkbox(label="使用 LLM 识别表结构", value=True)
                use_message_for_summary_revision = gr.Checkbox(
                    label="将本条消息用于修改总结",
                    value=False,
                    info="勾选后发送的内容将作为对当前综合总结的修改意见，由 AI 修订总结并回写到下方框",
                )
                send_btn = gr.Button("发送")
                summary_btn = gr.Button("生成综合总结")
                clear_btn = gr.Button("清空对话")

            with gr.Column(scale=4):
                summary_prompt_box = gr.Textbox(
                    label="综合总结提示词",
                    lines=10,
                    value=DEFAULT_SUMMARY_PROMPT,
                    placeholder="默认提示词会随对话自动追加「对话记录」；可在此编辑后再点「生成综合总结」。总结正文仅写入报告预览，不覆盖本框。",
                )
                report_html = gr.HTML(label="报告预览")
                report_file = gr.File(label="报告下载")

        send_btn.click(
            handle_message,
            inputs=[
                message,
                chatbot,
                uploads,
                state,
                sheet_name,
                time_window,
                use_llm_structure,
                use_message_for_summary_revision,
            ],
            outputs=[chatbot, state, report_html, report_file, summary_prompt_box],
        )
        message.submit(
            handle_message,
            inputs=[
                message,
                chatbot,
                uploads,
                state,
                sheet_name,
                time_window,
                use_llm_structure,
                use_message_for_summary_revision,
            ],
            outputs=[chatbot, state, report_html, report_file, summary_prompt_box],
        )
        summary_btn.click(
            handle_generate_summary,
            inputs=[chatbot, state, summary_prompt_box],
            outputs=[chatbot, state, report_html, report_file, summary_prompt_box],
        )

        def _clear():
            return [], SessionState(), "", None, DEFAULT_SUMMARY_PROMPT  # 清空后下一轮重新生成新 docx，总结框恢复默认提示词

        clear_btn.click(
            _clear,
            outputs=[chatbot, state, report_html, report_file, summary_prompt_box],
        )

    return demo


def main() -> None:
    parser = argparse.ArgumentParser(description="Gradio 数据分析 WebUI")
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="服务监听端口，默认 5600；未指定时可用环境变量 GRADIO_SERVER_PORT 覆盖。端口被占用时自动尝试 +1。",
    )
    args = parser.parse_args()
    demo = build_ui()
    # 端口优先级：--port > 环境变量 GRADIO_SERVER_PORT > 默认 5600
    if args.port is not None:
        base_port = args.port
    else:
        base_port = int(os.environ.get("GRADIO_SERVER_PORT", "5600"))
    last_error = None
    for attempt in range(5):
        port = base_port + attempt
        try:
            demo.launch(server_name="0.0.0.0", server_port=port)
            return
        except OSError as e:
            last_error = e
            # Windows 10048 / WSAEADDRINUSE、Linux/Mac 端口占用等
            err_str = str(e).lower()
            if any(
                x in err_str or x in str(e)
                for x in ("10048", "empty port", "only one usage", "address already in use", "errno 98", "eaddrinuse")
            ):
                continue
            raise
    if last_error is not None:
        raise last_error


if __name__ == "__main__":
    main()
