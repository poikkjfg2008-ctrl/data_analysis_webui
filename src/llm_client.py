import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, urlunparse

import requests


@dataclass
class LLMConfig:
    host: str
    port: int
    timeout_ms: int
    default_provider: str
    default_model: str
    api_base_url: str
    api_key: str


def _load_config(config_path: str) -> LLMConfig:
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    router_default = data.get("Router", {}).get("default", "")
    provider_name = ""
    model_name = ""
    if router_default:
        parts = [p.strip() for p in router_default.split(",") if p.strip()]
        if parts:
            provider_name = parts[0]
        if len(parts) > 1:
            model_name = parts[1]

    api_base_url = ""
    api_key = ""
    providers = data.get("Providers", [])
    if provider_name and isinstance(providers, list):
        for provider in providers:
            if not isinstance(provider, dict):
                continue
            if provider.get("name") == provider_name:
                api_base_url = str(provider.get("api_base_url", "")).strip()
                api_key = str(provider.get("api_key", "")).strip()
                break

    if not api_base_url or not api_key:
        missing_fields = []
        if not api_base_url:
            missing_fields.append("api_base_url")
        if not api_key:
            missing_fields.append("api_key")
        raise ValueError(
            "缺少 Azure 配置字段: "
            + ", ".join(missing_fields)
            + "（Providers / Router.default）"
        )

    return LLMConfig(
        host=data.get("HOST", "127.0.0.1"),
        port=int(data.get("PORT", 0)),
        timeout_ms=int(data.get("API_TIMEOUT_MS", 600000)),
        default_provider=provider_name,
        default_model=model_name,
        api_base_url=api_base_url,
        api_key=api_key,
    )


def _append_path(base_url: str, append_path: str) -> str:
    parsed = urlparse(base_url)
    base_path = parsed.path.rstrip("/")
    target = append_path.strip("/")

    if not base_path:
        new_path = f"/{target}"
    elif base_path.endswith(f"/{target}"):
        new_path = base_path
    elif base_path.endswith("/v1") and target.startswith("v1/"):
        new_path = f"{base_path}/{target[len('v1/') :]}"
    elif base_path.endswith("/openai") and target.startswith("openai/"):
        new_path = f"{base_path}/{target[len('openai/') :]}"
    elif base_path.endswith("/openai/v1") and target.startswith("openai/v1/"):
        new_path = f"{base_path}/{target[len('openai/v1/') :]}"
    else:
        new_path = f"{base_path}/{target}"

    return urlunparse((parsed.scheme, parsed.netloc, new_path, parsed.params, parsed.query, parsed.fragment))


def _build_response_urls(config: LLMConfig) -> List[str]:
    base_url = config.api_base_url.strip()
    if not base_url:
        raise ValueError("api_base_url 为空")
    parsed = urlparse(base_url)
    path = parsed.path.rstrip("/")
    urls = [_append_path(base_url, "responses")]
    if not path.endswith("/v1"):
        urls.append(_append_path(base_url, "v1/responses"))
    if "/openai" not in path and not path.endswith("/v1"):
        urls.append(_append_path(base_url, "openai/v1/responses"))
    ordered: List[str] = []
    seen = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        ordered.append(url)
    return ordered


def _build_chat_urls(config: LLMConfig) -> List[str]:
    base_url = config.api_base_url.strip()
    if not base_url:
        raise ValueError("api_base_url 为空")
    parsed = urlparse(base_url)
    path = parsed.path.rstrip("/")
    urls = [_append_path(base_url, "chat/completions")]
    if not path.endswith("/v1"):
        urls.append(_append_path(base_url, "v1/chat/completions"))
    if "/openai" not in path and not path.endswith("/v1"):
        urls.append(_append_path(base_url, "openai/v1/chat/completions"))
    ordered: List[str] = []
    seen = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        ordered.append(url)
    return ordered


def _post_with_multi_fallback(config: LLMConfig, request_candidates: List[Tuple[str, Dict[str, Any]]]) -> Dict[str, Any]:
    headers = {
        "api-key": config.api_key,
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }

    last_resp: Optional[requests.Response] = None
    for url, payload in request_candidates:
        resp = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=config.timeout_ms / 1000.0,
        )
        last_resp = resp
        if resp.status_code < 400:
            return resp.json()

        error_text = resp.text[:2000]
        print(f"[llm_client] 请求失败 {resp.status_code} {url}: {error_text}")

    if last_resp is None:
        raise ValueError("未能发送请求")
    last_resp.raise_for_status()
    return last_resp.json()


def _post_with_fallback(config: LLMConfig, payload: Dict[str, Any]) -> Dict[str, Any]:
    return _post_with_multi_fallback(config, [(_append_path(config.api_base_url.strip(), "responses"), payload)])


def _build_inference_payload(messages: List[Dict[str, str]], json_mode: bool) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "model": "",
        "input": messages,
    }
    if json_mode:
        payload["text"] = {"format": {"type": "json_object"}}
    return payload


def _build_inference_payload_v1(messages: List[Dict[str, str]], json_mode: bool) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "model": "",
        "input": [
            {
                "role": msg["role"],
                "content": [{"type": "input_text", "text": msg["content"]}],
            }
            for msg in messages
        ],
    }
    if json_mode:
        payload["text"] = {"format": {"type": "json_object"}}
    return payload


def _build_chat_completions_payload(messages: List[Dict[str, str]], json_mode: bool) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "model": "",
        "messages": messages,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    return payload


def _post_inference(config: LLMConfig, messages: List[Dict[str, str]], json_mode: bool) -> Dict[str, Any]:
    payload = _build_inference_payload(messages, json_mode)
    payload["model"] = config.default_model
    payload_v1 = _build_inference_payload_v1(messages, json_mode)
    payload_v1["model"] = config.default_model
    chat_payload = _build_chat_completions_payload(messages, json_mode)
    chat_payload["model"] = config.default_model

    request_candidates: List[Tuple[str, Dict[str, Any]]] = []
    for url in _build_response_urls(config):
        request_candidates.append((url, payload))
        request_candidates.append((url, payload_v1))
    for url in _build_chat_urls(config):
        request_candidates.append((url, chat_payload))

    return _post_with_multi_fallback(config, request_candidates)


def _post_inference_for_summary(config: LLMConfig, messages: List[Dict[str, str]]) -> Dict[str, Any]:
    return _post_inference(config, messages, json_mode=False)


def _build_message(role: str, content: str) -> Dict[str, str]:
    return {"role": role, "content": content}


def _safe_get(data: Any, *keys: Any) -> Optional[Any]:
    cur: Any = data
    for key in keys:
        if isinstance(key, int):
            if not isinstance(cur, list) or key >= len(cur):
                return None
            cur = cur[key]
            continue
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _extract_output_text(data: Dict[str, Any]) -> Optional[str]:
    if not isinstance(data, dict):
        return None
    output_text = _safe_get(data, "output_text")
    if output_text:
        return str(output_text).strip()

    output_items = _safe_get(data, "output")
    if isinstance(output_items, list):
        for item in output_items:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for piece in content:
                if not isinstance(piece, dict):
                    continue
                text_value = piece.get("text")
                if text_value:
                    return str(text_value).strip()

    fallback_text = _safe_get(data, "text")
    if isinstance(fallback_text, str) and fallback_text.strip():
        return fallback_text.strip()

    choices = _safe_get(data, "choices")
    if isinstance(choices, list):
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            message_content = _safe_get(choice, "message", "content")
            if isinstance(message_content, str) and message_content.strip():
                return message_content.strip()
            if isinstance(message_content, list):
                text_parts = []
                for item in message_content:
                    if isinstance(item, dict):
                        text_value = item.get("text")
                        if isinstance(text_value, str) and text_value.strip():
                            text_parts.append(text_value.strip())
                if text_parts:
                    return "\n".join(text_parts)
    return None


def _log_response_debug(data: Dict[str, Any]) -> None:
    snippet = json.dumps(data, ensure_ascii=False)[:2000]
    print(f"[llm_client] 响应调试: {snippet}")


def _log_raw_text_debug(text: str) -> None:
    snippet = str(text).replace("\n", "\\n")[:2000]
    print(f"[llm_client] 原始文本: {snippet}")


def _raise_if_error(data: Dict[str, Any]) -> None:
    error_info = _safe_get(data, "error")
    if error_info:
        raise ValueError(f"LLM 返回错误: {error_info}")
    return None


def _require_output_text(data: Dict[str, Any]) -> str:
    _raise_if_error(data)
    content_text = _extract_output_text(data)
    if not content_text:
        _log_response_debug(data)
        raise ValueError("LLM 返回内容为空")
    return content_text


def _parse_response_json(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        _log_raw_text_debug(text)

    cleaned = str(text).strip()
    if cleaned.startswith("```"):
        lines = [line for line in cleaned.splitlines() if line.strip()]
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            _log_raw_text_debug(cleaned)

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise
    candidate = cleaned[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        _log_raw_text_debug(candidate)

    candidate = cleaned[start : end + 1].replace("'", '"')
    return json.loads(candidate)


def analyze_excel_structure(
    config_path: str,
    column_names: List[str],
    sample_by_column: Dict[str, List[Any]],
    max_sample_values: int = 5,
) -> Dict[str, Any]:
    """
    由 LLM 根据列名与每列样本值推断：哪一列是日期列、哪些是数值指标列及展示名。
    返回: { "date_column": str, "numeric_columns": [ {"column": str, "display_name": str}, ... ] }
    """
    config = _load_config(config_path)
    system_prompt = (
        "你是数据分析助手。根据表格的「列名」和「每列前几条样本值」，推断表格结构。"
        "规则：1）日期列：仅选一列作为时间轴，该列应主要为日期或可解析为日期。"
        "2）数值指标列：列出所有表示业务数值的列（产量、率、价格、指数等），不要选纯日期列或明显为编号/ID 的列。"
        "3）若存在「名称列+数值列」成对（如一列是指标名、下一列是对应数值），只把「数值列」列入 numeric_columns，display_name 可用相邻名称列的内容或简写。"
        "4）display_name 用于报告与图表，无歧义时可与 column 相同。"
        "输出严格 JSON，不要多余文字。"
    )
    sample_text_parts = []
    for col in column_names[:80]:
        vals = sample_by_column.get(col, [])[:max_sample_values]
        vals_str = [str(v)[:30] for v in vals]
        sample_text_parts.append(f"  {col}: {vals_str}")
    sample_text = "\n".join(sample_text_parts)
    expected = {
        "date_column": "string（唯一作为时间轴的列名）",
        "numeric_columns": [{"column": "string", "display_name": "string"}],
    }
    user_content = (
        f"列名: {column_names}\n\n每列样本值（前{max_sample_values}个）:\n{sample_text}\n\n"
        f"请输出 JSON，结构参考: {json.dumps(expected, ensure_ascii=False)}"
    )
    messages = [
        _build_message("system", system_prompt),
        _build_message("user", user_content),
    ]
    payload = _post_inference(config, messages, json_mode=True)
    content_text = _require_output_text(payload)
    parsed = _parse_response_json(content_text)
    if not isinstance(parsed, dict):
        raise ValueError("LLM 返回结果不是 JSON 对象")
    return parsed


def parse_prompt(
    config_path: str,
    user_prompt: str,
    columns: List[str],
    date_range: Tuple[str, str],
    sheets: List[str],
) -> Dict[str, Any]:
    config = _load_config(config_path)

    system_prompt = (
        "你是数据分析助手。根据用户的描述，从给定列名中选择指标，并解析时间窗口。"
        "仅选择用户明确提及的指标名称；如果用户未明确提及任何指标且未要求全部/所有/全部指标/所有指标/全部列/所有列，"
        "indicator_names 返回空列表；如果用户明确要求全部指标，可返回空列表或列出全部（由服务端处理）。"
        "输出严格的 JSON，不要添加多余文字。"
    )

    expected_schema = {
        "indicator_names": ["string"],
        "time_window": {
            "type": "relative|absolute",
            "value": "最近一年/最近一周/最近N天 或 YYYY-MM-DD 至 YYYY-MM-DD",
        },
        "sheet_name": "string or null",
    }

    messages = [
        _build_message("system", system_prompt),
        _build_message(
            "user",
            (
                f"请根据以下信息解析需求。\n"
                f"用户描述: {user_prompt}\n"
                f"可用列: {columns}\n"
                f"可用工作表: {sheets}\n"
                f"日期范围: {date_range[0]} ~ {date_range[1]}\n"
                "示例：\n"
                "- 用户描述未点名指标，仅说'分析最近一年趋势' -> indicator_names 返回 []。\n"
                "- 用户描述要求'全部指标'或'所有指标' -> indicator_names 返回 [] 或列出全部。\n"
                f"请输出 JSON，字段结构示例: {json.dumps(expected_schema, ensure_ascii=False)}"
            ),
        ),
    ]

    payload = _post_inference(config, messages, json_mode=True)
    content_text = _require_output_text(payload)
    parsed = _parse_response_json(content_text)

    if not isinstance(parsed, dict):
        raise ValueError("LLM 返回结果不是 JSON 对象")

    return parsed


def match_indicators_similarity(
    config_path: str,
    user_prompt: str,
    columns_with_display: List[Dict[str, str]],
) -> Dict[str, Any]:
    """
    根据用户描述对指标列做相似匹配。
    返回:
      - status="ok", indicator_names=[...]  唯一匹配
      - status="not_found", message="..."  无相似列
      - status="ambiguous", candidates=[{display, column}, ...], message="..."  多列相似需用户选择
    """
    config = _load_config(config_path)
    system_prompt = (
        "你是数据分析助手。根据用户描述，从「可用列」中做相似匹配（含简称、别名、部分匹配）。"
        "规则：1）若没有任何列与用户描述相似，返回 status=not_found 和简短 message。"
        "2）若唯一确定一列或若干列，返回 status=ok 和 indicator_names（列名用 display）。"
        "3）若有多个相似列且无法唯一确定用户要哪几个，返回 status=ambiguous、candidates 列表（每项含 display 与 column）和简短 message 建议用户选择。"
        "输出严格 JSON，不要多余文字。"
    )
    expected = {
        "status": "ok|not_found|ambiguous",
        "indicator_names": ["string"],
        "message": "string or null",
        "candidates": [{"display": "string", "column": "string"}],
    }
    messages = [
        _build_message("system", system_prompt),
        _build_message(
            "user",
            (
                f"用户描述: {user_prompt}\n"
                f"可用列（display 为展示名，column 为实际列名）:\n{json.dumps(columns_with_display, ensure_ascii=False)}\n"
                f"请输出 JSON，结构参考: {json.dumps(expected, ensure_ascii=False)}"
            ),
        ),
    ]
    payload = _post_inference(config, messages, json_mode=True)
    content_text = _require_output_text(payload)
    parsed = _parse_response_json(content_text)
    if not isinstance(parsed, dict):
        raise ValueError("LLM 返回结果不是 JSON 对象")
    return parsed


def infer_metric_unit(
    config_path: str,
    metric_name: str,
    excel_unit: Optional[str] = None,
) -> str:
    """
    综合指标名称与（若有）Excel 解析出的单位，由 LLM 判断图表纵轴应标注的单位。
    例如：Excel 单位「旬」在「粗钢重点企业(旬)」里多为时间口径→推断「万吨」；在「工作时间(旬)」里可为真实单位→保留「旬」。
    返回简短单位字符串，无则返回空。
    """
    config = _load_config(config_path)
    system_prompt = (
        "你是数据分析助手。根据「指标名称」和「Excel 解析出的单位」（若有），综合判断图表纵轴应标注的单位。"
        "规则：若 Excel 单位只是指标的时间口径（如旬报、周报里的旬/周），并非数值的计量单位，则根据指标含义推断数值单位（如万吨、%、元、辆）；"
        "若 Excel 单位本身就是合理的数值单位（如工作时间的旬、某周期数），则可沿用。结合上下文自行判断，不要死板规则。"
        "只返回单位本身，2-6 个汉字或符号，不要引号、不要解释；无法确定则返回空。"
    )
    user_content = f"指标名称: {metric_name}"
    if excel_unit and str(excel_unit).strip():
        user_content += f"\nExcel 解析出的单位: {excel_unit.strip()}"
    user_content += "\n请直接给出纵轴单位（如 万吨、%、旬、元），没有则输出空:"
    messages = [
        _build_message("system", system_prompt),
        _build_message("user", user_content),
    ]
    try:
        payload = _post_inference(config, messages, json_mode=False)
        content_text = _require_output_text(payload)
        unit = str(content_text).strip().strip('"\'')[:20]
        return unit if unit and unit != "空" else ""
    except Exception:
        return ""


def generate_summary(
    config_path: str,
    metric_name: str,
    stats: Dict[str, Any],
    window_desc: str,
) -> str:
    config = _load_config(config_path)

    system_prompt = "你是数据分析助手，请基于统计结果给出简洁结论。"
    user_payload = {
        "metric": metric_name,
        "window": window_desc,
        "stats": stats,
    }

    messages = [
        _build_message("system", system_prompt),
        _build_message(
            "user",
            "请基于以下 JSON 生成 2-3 句中文结论：\n"
            f"{json.dumps(user_payload, ensure_ascii=False)}",
        ),
    ]

    payload = _post_inference_for_summary(config, messages)
    content_text = _require_output_text(payload)
    return str(content_text).strip()


def generate_conversation_summary(
    config_path: str,
    conversation_text: str,
    user_prompt_override: Optional[str] = None,
    report_content: Optional[str] = None,
) -> str:
    """根据多轮对话与报告中的数据生成综合总结。
    user_prompt_override: 若提供则作为完整用户消息（前端可能已含对话记录）。
    report_content: 报告中各指标的标题与统计表（均值、期初期末、变化率等），供模型基于真实数据概括趋势。"""
    config = _load_config(config_path)
    system_prompt = (
        "你是数据分析报告撰写助手。请结合「对话记录」与「报告中的数据」撰写「综合总结」。\n"
        "报告中的数据包含各指标的名称、日期范围、以及统计表（计数、平均值、最小值、最大值、期初、期末、绝对变化、变化率等）。"
        "请基于这些真实数据概括各指标的趋势、波动与结论（如同比/环比含义、波动区间、季节性等），"
        "并可基于指标含义简要提及可能的影响因素（需求、政策、供给等），仅基于常识推断、勿编造具体数据。"
        "若有多类指标，可做简要联动分析。输出纯文本、分段清晰、2–5 段、中文。不要输出 JSON 或标题外的多余格式。"
    )
    if (user_prompt_override or "").strip():
        user_content = (user_prompt_override or "").strip()
    else:
        user_content = (
            "请基于以下对话记录生成综合总结：\n\n" + (conversation_text or "（无对话内容）")
        )
    if (report_content or "").strip():
        user_content += (
            "\n\n【以下为报告中各指标的标题与统计表，请结合这些数据撰写总结】\n\n"
            + (report_content or "").strip()
        )
    messages = [
        _build_message("system", system_prompt),
        _build_message("user", user_content),
    ]
    payload = _post_inference_for_summary(config, messages)
    content_text = _require_output_text(payload)
    return str(content_text).strip()


def revise_summary(
    config_path: str,
    current_summary: str,
    revision_instruction: str,
) -> str:
    """根据用户修改意见，在现有总结基础上修订并返回新的完整总结正文。"""
    config = _load_config(config_path)
    system_prompt = (
        "你是数据分析报告撰写助手。用户会对当前「综合总结」提出修改意见，"
        "请根据意见修改总结内容，只输出修改后的完整总结正文（纯文本、分段清晰、中文），不要输出解释或标题。"
    )
    user_content = (
        "当前总结：\n\n"
        + (current_summary or "（无）")
        + "\n\n用户修改意见：\n"
        + (revision_instruction or "（无）")
    )
    messages = [
        _build_message("system", system_prompt),
        _build_message("user", user_content),
    ]
    payload = _post_inference_for_summary(config, messages)
    content_text = _require_output_text(payload)
    return str(content_text).strip()
