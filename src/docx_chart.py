# -*- coding: utf-8 -*-
"""
在 docx 中插入可编辑的 OOXML 折线图（非图片），横纵轴可在 Word 中编辑。
"""
from __future__ import annotations

import os
import re
import shutil
import tempfile
import zipfile
from typing import List, Optional, Tuple

# OOXML 命名空间
C_NS = "http://schemas.openxmlformats.org/drawingml/2006/chart"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _escape_xml(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _axis_scale_and_label(values: List[float]) -> tuple:
    """按数值大小决定是否用万/亿：满亿用亿、满万用万，否则不缩放；返回 (缩放后数值列表, 纵轴标题)。"""
    if not values:
        return [], "数值"
    try:
        max_abs = max(abs(float(v)) for v in values if v is not None)
    except (TypeError, ValueError):
        return list(values), "数值"
    if max_abs >= 1e8:
        scale = 1e8
        label = "数值(亿)"
    elif max_abs >= 1e4:
        scale = 1e4
        label = "数值(万)"
    else:
        scale = 1.0
        label = "数值"
    scaled = [(float(v) / scale) if v is not None else 0.0 for v in values]
    return scaled, label


def _build_chart_part_xml(
    categories: List[str],
    values: List[float],
    chart_title: str,
    unit: Optional[str] = None,
) -> str:
    """生成折线图 chart part 的 XML。满万/亿时纵轴用万/亿；纵轴标注实际单位（元/辆等）。折线统一单色。"""
    scaled_values, scale_label = _axis_scale_and_label(values)
    values_to_use = scaled_values if scaled_values else values
    pt_count = len(values_to_use)
    if pt_count == 0:
        pt_count = 1
    # 纵轴只标注单位，格式为（单位），如（%）、（亿吨），不要「数值（%）」
    if unit and str(unit).strip():
        axis_label = f"（{str(unit).strip()}）"
    elif scale_label == "数值(万)":
        axis_label = "（万）"
    elif scale_label == "数值(亿)":
        axis_label = "（亿）"
    else:
        axis_label = ""
    cat_pts = "".join(
        f'<c:pt idx="{i}"><c:v>{_escape_xml(str(categories[i]) if i < len(categories) else "")}</c:v></c:pt>'
        for i in range(max(len(categories), pt_count))
    )
    val_pts = "".join(
        f'<c:pt idx="{i}"><c:v>{values_to_use[i] if i < len(values_to_use) else 0}</c:v></c:pt>'
        for i in range(pt_count)
    )
    title_esc = _escape_xml(chart_title)[:255]
    axis_label_esc = _escape_xml(axis_label)
    val_ax_title_xml = f"""
        <c:title>
          <c:tx>
            <c:rich>
              <a:bodyPr/><a:lstStyle/>
              <a:p><a:r><a:t>{axis_label_esc}</a:t></a:r></a:p>
            </c:rich>
          </c:tx>
          <c:overlay val="0"/>
          <c:spPr/>
          <c:txPr>
            <a:bodyPr/><a:lstStyle/>
            <a:p><a:pPr><a:defRPr sz="900"/></a:pPr><a:endParaRPr lang="zh-CN"/></a:p>
          </c:txPr>
        </c:title>""" if axis_label else ""
    # 折线统一单色（蓝色），不按段分色
    line_sp_pr = """<c:spPr>
          <a:ln w="28575">
            <a:solidFill><a:srgbClr val="2567B8"/></a:solidFill>
            <a:round/>
          </a:ln>
        </c:spPr>"""
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<c:chartSpace xmlns:c="{C_NS}" xmlns:a="{A_NS}">
  <c:date1904 val="0"/>
  <c:lang val="zh-CN"/>
  <c:roundedCorners val="0"/>
  <c:chart>
    <c:title>
      <c:tx>
        <c:rich>
          <a:bodyPr/>
          <a:lstStyle/>
          <a:p>
            <a:r>
              <a:t>{title_esc}</a:t>
            </a:r>
          </a:p>
        </c:rich>
      </c:tx>
      <c:overlay val="0"/>
      <c:spPr/>
      <c:txPr>
        <a:bodyPr/>
        <a:lstStyle/>
        <a:p>
          <a:pPr>
            <a:defRPr sz="1200"/>
          </a:pPr>
          <a:endParaRPr lang="zh-CN"/>
        </a:p>
      </c:txPr>
    </c:title>
    <c:plotArea>
      <c:layout/>
      <c:lineChart>
        <c:grouping val="standard"/>
        <c:ser>
          <c:idx val="0"/>
          <c:order val="0"/>
          <c:cat>
            <c:strRef>
              <c:f>Sheet1!$A$2:$A${max(len(categories), pt_count) + 1}</c:f>
              <c:strCache>
                <c:ptCount val="{max(len(categories), pt_count)}"/>
                {cat_pts}
              </c:strCache>
            </c:strRef>
          </c:cat>
          <c:val>
            <c:numRef>
              <c:f>Sheet1!$B$2:$B${pt_count + 1}</c:f>
              <c:numCache>
                <c:formatCode>General</c:formatCode>
                <c:ptCount val="{pt_count}"/>
                {val_pts}
              </c:numCache>
            </c:numRef>
          </c:val>
          <c:smooth val="0"/>
          <c:marker>
            <c:symbol val="circle"/>
            <c:size val="5"/>
          </c:marker>
          {line_sp_pr}
        </c:ser>
        <c:axId val="1"/>
        <c:axId val="2"/>
      </c:lineChart>
      <c:catAx>
        <c:axId val="1"/>
        <c:scaling><c:orientation val="minMax"/></c:scaling>
        <c:delete val="0"/>
        <c:axPos val="b"/>
        <c:crossAx val="2"/>
        <c:crosses val="autoZero"/>
        <c:auto val="1"/>
        <c:lblAlgn val="ctr"/>
        <c:lblOffset val="100"/>
        <c:tickLblPos val="nextTo"/>
        <c:spPr/>
        <c:txPr>
          <a:bodyPr rot="-5400000"/>
          <a:lstStyle/>
          <a:p>
            <a:pPr><a:defRPr sz="900"/></a:pPr>
            <a:endParaRPr lang="zh-CN"/>
          </a:p>
        </c:txPr>
        <c:crossesAt val="0"/>
        <c:majorTickMark val="out"/>
        <c:minorTickMark val="none"/>
        <c:tickLblSkip val="1"/>
      </c:catAx>
      <c:valAx>
        <c:axId val="2"/>{val_ax_title_xml}
        <c:scaling><c:orientation val="minMax"/></c:scaling>
        <c:delete val="0"/>
        <c:axPos val="l"/>
        <c:crossAx val="1"/>
        <c:crosses val="autoZero"/>
        <c:crossesAt val="0"/>
        <c:auto val="1"/>
        <c:lblAlgn val="ctr"/>
        <c:lblOffset val="100"/>
        <c:tickLblPos val="nextTo"/>
        <c:spPr/>
        <c:txPr>
          <a:bodyPr/>
          <a:lstStyle/>
          <a:p>
            <a:pPr><a:defRPr sz="900"/></a:pPr>
            <a:endParaRPr lang="zh-CN"/>
          </a:p>
        </c:txPr>
        <c:majorTickMark val="out"/>
        <c:minorTickMark val="none"/>
      </c:valAx>
      <c:spPr/>
    </c:plotArea>
    <c:plotVisOnly val="1"/>
    <c:dispBlanksAs val="gap"/>
  </c:chart>
  <c:spPr/>
  <c:txPr>
    <a:bodyPr/>
    <a:lstStyle/>
    <a:p><a:pPr><a:defRPr/></a:pPr></a:p>
  </c:txPr>
</c:chartSpace>
"""


def _build_drawing_xml(r_id: str) -> str:
    """生成嵌入图表的 drawing 片段（在段落内使用），图表在 Word 中可编辑。"""
    return f"""<w:drawing xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <wp:inline distT="0" distB="0" distL="0" distR="0">
    <wp:extent cx="5000000" cy="2800000"/>
    <wp:effectExtent l="0" t="0" r="0" b="0"/>
    <wp:docPr id="1" name="Chart 1" descr=""/>
    <wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>
    <a:graphic>
      <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/chart">
        <c:chart xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" r:id="{r_id}"/>
      </a:graphicData>
    </a:graphic>
  </wp:inline>
</w:drawing>"""


CHART_PLACEHOLDER_PREFIX = "CHART_PLACEHOLDER_"


def inject_editable_charts(
    docx_path: str,
    charts_data: List[Tuple[List[str], List[float], str, Optional[str]]],
) -> None:
    """
    向已保存的 docx 注入可编辑折线图，替换占位段落。
    charts_data: [(categories, values, title, unit), ...]，unit 为纵轴实际单位（元/辆等），可空。
    仅处理文档中实际存在的占位符，避免多轮追加时重复 PartName/Relationship 导致 Word 报「无法读取的内容」。
    """
    tmpdir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(docx_path, "r") as z:
            z.extractall(tmpdir)
        word_dir = os.path.join(tmpdir, "word")
        charts_dir = os.path.join(word_dir, "charts")
        rels_dir = os.path.join(word_dir, "_rels")
        os.makedirs(charts_dir, exist_ok=True)

        doc_path = os.path.join(word_dir, "document.xml")
        rels_path = os.path.join(rels_dir, "document.xml.rels")
        with open(doc_path, "r", encoding="utf-8") as f:
            doc_xml = f.read()
        with open(rels_path, "r", encoding="utf-8") as f:
            rels_xml = f.read()

        # 只处理文档里真实存在的占位符，避免多轮注入时重复 PartName/rels 损坏 docx
        existing_placeholder_indices = [
            idx
            for idx in range(len(charts_data))
            if doc_xml.find(f"{CHART_PLACEHOLDER_PREFIX}{idx}") != -1
        ]
        if not existing_placeholder_indices:
            return

        next_r_id = 1
        for existing in re.findall(r'Relationship Id="rId(\d+)"', rels_xml):
            next_r_id = max(next_r_id, int(existing) + 1)
        # 新图表使用不重复的文件名，避免覆盖已有 chart 并导致 Content Types 重复
        existing_chart_nums = [
            int(m)
            for m in re.findall(r'Target="charts/chart(\d+)\.xml"', rels_xml)
        ]
        next_chart_num = max(existing_chart_nums, default=0) + 1

        rels_to_append = []
        chart_id_by_index = {}

        for i, idx in enumerate(existing_placeholder_indices):
            item = charts_data[idx]
            categories = item[0]
            values = item[1]
            title = item[2]
            unit = item[3] if len(item) > 3 else None
            chart_part_name = f"chart{next_chart_num + i}.xml"
            r_id = f"rId{next_r_id}"
            next_r_id += 1
            chart_id_by_index[idx] = (r_id, chart_part_name)
            chart_xml = _build_chart_part_xml(categories, values, title, unit=unit)
            with open(
                os.path.join(charts_dir, chart_part_name),
                "w",
                encoding="utf-8",
            ) as f:
                f.write(chart_xml)
            rels_to_append.append(
                f'  <Relationship Id="{r_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/chart" Target="charts/{chart_part_name}"/>'
            )

        for idx in existing_placeholder_indices:
            placeholder = f"{CHART_PLACEHOLDER_PREFIX}{idx}"
            r_id, _ = chart_id_by_index[idx]
            drawing = _build_drawing_xml(r_id)
            pos = doc_xml.find(placeholder)
            if pos == -1:
                continue
            p_start = doc_xml.rfind("<w:p", 0, pos)
            p_end = doc_xml.find("</w:p>", pos) + len("</w:p>")
            if p_start != -1 and p_end > pos:
                doc_xml = (
                    doc_xml[:p_start]
                    + f"<w:p><w:r>{drawing}</w:r></w:p>"
                    + doc_xml[p_end:]
                )

        rels_insert = rels_xml.rstrip()
        if not rels_insert.endswith("</Relationships>"):
            rels_to_append.append("</Relationships>")
            rels_insert += "\n" + "\n".join(rels_to_append)
        else:
            rels_insert = rels_insert.replace(
                "</Relationships>",
                "\n" + "\n".join(rels_to_append) + "\n</Relationships>",
            )
        with open(rels_path, "w", encoding="utf-8") as f:
            f.write(rels_insert)
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write(doc_xml)

        content_types_path = os.path.join(tmpdir, "[Content_Types].xml")
        with open(content_types_path, "r", encoding="utf-8") as f:
            ct = f.read()
        # 只为本次新加的 chart 文件添加 Override，避免重复 PartName
        overrides = "".join(
            f'<Override PartName="/word/charts/{chart_id_by_index[idx][1]}" ContentType="application/vnd.openxmlformats-officedocument.drawingml.chart+xml"/>'
            for idx in existing_placeholder_indices
        )
        ct = ct.replace("</Types>", overrides + "</Types>")
        with open(content_types_path, "w", encoding="utf-8") as f:
            f.write(ct)

        with zipfile.ZipFile(docx_path, "w", zipfile.ZIP_DEFLATED) as z:
            for root, _, files in os.walk(tmpdir):
                for name in files:
                    path = os.path.join(root, name)
                    arcname = os.path.relpath(path, tmpdir).replace("\\", "/")
                    z.write(path, arcname)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
