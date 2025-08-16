from __future__ import annotations
from io import BytesIO
from typing import Dict, Any
from datetime import datetime
import os
import streamlit as st

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage

def _kv_table(data: Dict[str, Any], col1: str = "欄位", col2: str = "內容"):
    rows = [[col1, col2]] + [[str(k), str(v)] for k, v in data.items()]
    t = Table(rows, colWidths=[140, 360])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F9FAFB")]),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,0), 6),
        ("TOPPADDING", (0,0), (-1,0), 6),
    ]))
    return t

def _try_logo(story):
    brand = st.secrets.get("brand", {})
    logo_url = brand.get("logo_url", "")
    # 先試品牌 URL；不行則載入本地佔位
    tried = False
    if logo_url:
        try:
            story.append(RLImage(logo_url, width=120, height=120 * 0.28))
            tried = True
        except Exception:
            pass
    if not tried:
        local = os.path.join("assets", "logo_placeholder.png")
        if os.path.exists(local):
            try:
                story.append(RLImage(local, width=120, height=120 * 0.28))
            except Exception:
                pass

def build_pdf(*, inputs_summary: Dict[str, Any], result_summary: Dict[str, Any], recommendations: Dict[str, Any], comparisons: Dict[str, Any] | None = None) -> bytes:
    brand = st.secrets.get("brand", {})
    brand_title = brand.get("title", "Grace Family Office｜永傳家族辦公室")
    footer = brand.get("footer", "")

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()

    story = []
    _try_logo(story)

    title = Paragraph(
        f"<para align='left'><font size=18><b>{brand_title}</b></font><br/><font size=12>顧問建議報告｜{datetime.now().strftime('%Y-%m-%d')}</font></para>",
        styles["Normal"],
    )
    story += [title, Spacer(1, 12)]

    story.append(Paragraph("<b>一、您的基本情境</b>", styles["Heading3"]))
    story.append(_kv_table(inputs_summary))
    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>二、重點結果摘要</b>", styles["Heading3"]))
    story.append(_kv_table(result_summary, "項目", "數值／說明"))
    story.append(Spacer(1, 12))

    if comparisons:
        story.append(Paragraph("<b>三、情境比較（基準 vs. 規劃）</b>", styles["Heading3"]))
        rows = [["情境", "稅費合計", "備註"]]
        for name, info in comparisons.items():
            rows.append([name, str(info.get("total_tax", "-")), info.get("note", "")])
        t = Table(rows, colWidths=[160, 130, 210])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0F766E")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#D1FAE5")),
            ("FONTSIZE", (0,0), (-1,-1), 10),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#ECFEFF")]),
        ]))
        story.append(t)
        story.append(Spacer(1, 12))

    story.append(Paragraph("<b>四、顧問建議</b>", styles["Heading3"]))
    story.append(_kv_table(recommendations, "重點", "說明"))
    story.append(Spacer(1, 18))

    if footer:
        story.append(Paragraph(footer.replace("\n", "<br/>"), styles["Normal"]))

    doc.build(story)
    return buffer.getvalue()
