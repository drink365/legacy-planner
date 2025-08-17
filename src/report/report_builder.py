from __future__ import annotations
from io import BytesIO
from typing import Dict, Any, Tuple
from datetime import datetime
import os
import re
import streamlit as st

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ========= 1) 繁中字型（請將 TTF 放在 assets/fonts/ 下） =========
FONT_DIR = os.path.join("assets", "fonts")
REGULAR_TTF = os.path.join(FONT_DIR, "NotoSansTC-Regular.ttf")
BOLD_TTF    = os.path.join(FONT_DIR, "NotoSansTC-Bold.ttf")

def _register_fonts() -> Tuple[str, str]:
    try:
        if os.path.exists(REGULAR_TTF) and os.path.exists(BOLD_TTF):
            pdfmetrics.registerFont(TTFont("NotoTC", REGULAR_TTF))
            pdfmetrics.registerFont(TTFont("NotoTC-Bold", BOLD_TTF))
            return "NotoTC", "NotoTC-Bold"
    except Exception:
        pass
    return "Helvetica", "Helvetica-Bold"

BASE_FONT, BASE_FONT_BOLD = _register_fonts()

# ========= 2) Logo：本地優先 → secrets.logo_url → 佔位圖 =========
def _try_logo(story) -> bool:
    """回傳是否成功放置了 logo，用來決定是否顯示品牌大標"""
    # ① 本地 logo.png
    local = os.path.join("assets", "logo.png")
    if os.path.exists(local):
        try:
            story.append(RLImage(local, width=180, height=180 * 0.28))
            story.append(Spacer(1, 10))  # 與後續文字留白
            return True
        except Exception:
            pass

    # ② secrets logo_url
    brand = st.secrets.get("brand", {})
    logo_url = brand.get("logo_url", "")
    if logo_url:
        try:
            story.append(RLImage(logo_url, width=180, height=180 * 0.28))
            story.append(Spacer(1, 10))
            return True
        except Exception:
            pass

    # ③ 佔位圖
    placeholder = os.path.join("assets", "logo_placeholder.png")
    if os.path.exists(placeholder):
        try:
            story.append(RLImage(placeholder, width=180, height=180 * 0.28))
            story.append(Spacer(1, 10))
            return True
        except Exception:
            pass
    return False

# ========= 3) 小工具 =========
def _kv_table(data: Dict[str, Any], col1: str = "欄位", col2: str = "內容"):
    rows = [[col1, col2]] + [[str(k), str(v)] for k, v in data.items()]
    t = Table(rows, colWidths=[140, 360])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), BASE_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 10),

        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), BASE_FONT_BOLD),

        ("ALIGN", (0,0), (-1,-1), "LEFT"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F9FAFB")]),
        ("BOTTOMPADDING", (0,0), (-1,0), 6),
        ("TOPPADDING", (0,0), (-1,0), 6),
    ]))
    return t

def _sanitize_inputs(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """將『配偶＋二子女』等 +/＋ 改成頓號，避免誤讀為『十二』"""
    clean = dict(inputs)
    for key in ["家庭成員", "家庭成员"]:
        if key in clean and isinstance(clean[key], str):
            clean[key] = re.sub(r"[+＋]", "、", clean[key])
    return clean

def _derive_kpi_from_comparisons(comparisons: Dict[str, Any]) -> Dict[str, Any]:
    """
    從情境比較自動產出摘要 KPI，避免與表格重複：
      - 建議方案（最低稅額）
      - 節省金額
      - 降幅 %
    """
    if not comparisons:
        return {}

    # 找 baseline（名稱含「不規劃」或「基準」，找不到就用最大值）
    baseline_key = None
    for k in comparisons.keys():
        if "不規劃" in k or "基準" in k:
            baseline_key = k
            break
    # 取最大值作為基準的保底策略
    if baseline_key is None:
        baseline_key = max(comparisons, key=lambda x: float(comparisons[x].get("total_tax", 0) or 0))

    baseline_tax = float(comparisons[baseline_key].get("total_tax", 0) or 0)

    # 找最佳（最低稅額）的規劃方案（排除 baseline）
    candidates = {k: v for k, v in comparisons.items() if k != baseline_key}
    best_key = min(candidates, key=lambda x: float(candidates[x].get("total_tax", 0) or 0)) if candidates else baseline_key
    best_tax = float(comparisons[best_key].get("total_tax", 0) or 0)

    saved = max(baseline_tax - best_tax, 0)
    pct = f"{(saved / baseline_tax * 100):.0f}%" if baseline_tax > 0 else "-"

    return {
        "建議方案": best_key,
        "預估節省": f"{int(saved)} 萬（示意）",
        "降幅": pct,
    }

# ========= 4) 產生 PDF =========
def build_pdf(
    *,
    inputs_summary: Dict[str, Any],
    result_summary: Dict[str, Any],
    recommendations: Dict[str, Any],
    comparisons: Dict[str, Any] | None = None
) -> bytes:

    brand = st.secrets.get("brand", {})
    brand_title = brand.get("title", "Grace Family Office｜永傳家族辦公室")
    footer = brand.get("footer", "")
    show_title_below_logo = bool(brand.get("show_title_below_logo", False))  # 有 logo 時預設不顯示大標

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=40
    )
    styles = getSampleStyleSheet()
    styles["Normal"].fontName = BASE_FONT
    styles["Normal"].fontSize = 11
    styles["Heading3"].fontName = BASE_FONT_BOLD
    styles["Heading3"].fontSize = 13

    story = []

    # Header：Logo（若有則預設不再顯示大品牌名，避免重複）
    has_logo = _try_logo(story)

    title_style = ParagraphStyle(
        "TitleTW", parent=styles["Normal"],
        fontName=BASE_FONT_BOLD, fontSize=20, leading=24
    )
    subtitle_style = ParagraphStyle(
        "SubtitleTW", parent=styles["Normal"],
        fontName=BASE_FONT, fontSize=12, leading=16
    )

    if (not has_logo) or show_title_below_logo:
        story.append(Paragraph(brand_title, title_style))
        story.append(Spacer(1, 4))
    story.append(Paragraph(f"顧問建議報告｜{datetime.now().strftime('%Y-%m-%d')}", subtitle_style))
    story.append(Spacer(1, 12))

    # 一、基本情境（含「＋」→「、」的清理）
    clean_inputs = _sanitize_inputs(inputs_summary)
    story.append(Paragraph("一、您的基本情境", styles["Heading3"]))
    story.append(_kv_table(clean_inputs))
    story.append(Spacer(1, 12))

    # 二、重點結果摘要（若有 comparisons，改為 KPI 精華，避免與表格重複）
    story.append(Paragraph("二、重點結果摘要", styles["Heading3"]))
    if comparisons:
        kpi = _derive_kpi_from_comparisons(comparisons)
        # 將 KPI 與原本摘要合併（KPI 置頂）
        merged = {**kpi, **result_summary}
        story.append(_kv_table(merged, "項目", "數值／說明"))
    else:
        story.append(_kv_table(result_summary, "項目", "數值／說明"))
    story.append(Spacer(1, 12))

    # 三、情境比較（基準 vs. 規劃）
    if comparisons:
        story.append(Paragraph("三、情境比較（基準 vs. 規劃）", styles["Heading3"]))
        rows = [["情境", "稅費合計", "備註"]]
        for name, info in comparisons.items():
            rows.append([name, str(info.get("total_tax", "-")), info.get("note", "")])
        t = Table(rows, colWidths=[160, 130, 210])
        t.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), BASE_FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 10),

            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0F766E")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), BASE_FONT_BOLD),

            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#D1FAE5")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#ECFEFF")]),
        ]))
        story.append(t)
        story.append(Spacer(1, 12))

    # 四、顧問建議
    story.append(Paragraph("四、顧問建議", styles["Heading3"]))
    story.append(_kv_table(recommendations, "重點", "說明"))
    story.append(Spacer(1, 18))

    if footer:
        story.append(Paragraph(footer.replace("\n", "<br/>"), styles["Normal"]))

    doc.build(story)
    return buffer.getvalue()
