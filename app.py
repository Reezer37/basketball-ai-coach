import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from html import escape
from io import BytesIO
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
import streamlit as st
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_FEEDBACK_URL = "https://tally.so/r/oblEQO"

LANG_OPTIONS = {
    "Deutsch": "de",
    "English": "en",
    "中文": "zh",
}

TEXT = {
    "en": {
        "page_title": "Basketball Shot Form Check",
        "eyebrow": "Video shot report",
        "title": "Basketball Shot Form Check",
        "desc": "Upload one or more shooting clips and get a structured form report: release pose, mechanics, consistency, and practical next-step drills.",
        "language": "Language",
        "settings": "Session setup",
        "style_label": "Reference style",
        "mode_label": "Feedback mode",
        "source_label": "Video source",
        "source_record": "Record with phone camera",
        "source_upload": "Upload existing video",
        "upload_label": "Upload shooting video",
        "record_upload_label": "Record or choose shooting videos",
        "record_hint": "A single clip may include shooting, retrieving the ball, dribbling, walking, and shooting again. Keep the player visible between shots.",
        "upload_help": "The button may still say Upload. On phones, it opens the camera or photo/video library.",
        "record_checklist_title": "Before recording, check this:",
        "record_checklist": """
- Best result: film 5 or more shots in one clip
- Fewer shots still work, but stability feedback will be less certain
- Walking, dribbling, or retrieving the ball between shots is okay
- Use the same player, camera angle, and distance for consistency analysis
- Use landscape or portrait, but keep the full body visible
- Stand 2-4 meters from the camera
- Best angle: side view or about 45 degrees
- Keep feet, knees, shooting hand, and follow-through in frame
- Good light, steady phone, no slow-motion or edits
- If upload fails, record a shorter 1080p clip instead of 4K/HDR
""",
        "api_settings": "AI API settings",
        "api_settings_help": "For local testing only. Keys are used for this session and are not saved in code.",
        "provider_label": "AI provider",
        "provider_auto": "Auto",
        "provider_openai": "OpenAI",
        "provider_gemini": "Gemini",
        "openai_key_label": "OpenAI API key",
        "gemini_key_label": "Gemini API key",
        "model_label": "Model override (optional)",
        "missing_key": "Add an API key in AI API settings before generating the report notes.",
        "file_too_large": "This video is too large. Please upload a file up to {max_mb} MB. If you recorded on a phone, use a shorter clip or 1080p instead of 4K/HDR.",
        "unsupported_file": "Please choose a video file. Photos or unsupported files cannot be analyzed.",
        "upload_summary": "{count} video(s) selected.",
        "cooldown": "Please wait {seconds} more seconds before starting another analysis.",
        "start_label": "Start analysis",
        "payment_required_title": "Step 1: buy the beta report",
        "payment_required_body": "Pay securely first. After checkout, Stripe returns you here to upload your video and generate the report.",
        "payment_button_label": "Pay 1.99 Euro with Stripe",
        "payment_pending": "Payment is required before upload and report generation. After checkout, return through the payment success link to unlock the upload area.",
        "payment_unlocked": "Payment return detected. You can now upload your video and generate the report.",
        "payment_config_missing": "Payment is enabled, but PAYMENT_ACCESS_TOKEN is missing. Add it to Streamlit Secrets and set the Stripe success URL to return with that token.",
        "payment_link_missing": "Payment link is not configured yet, so analysis is open for testing.",
        "download_report": "Download report PDF",
        "support_title": "Feedback, problems, or refund request",
        "support_body": "If the report fails, feels wrong, or you want a refund, contact us with the payment email and a short note.",
        "support_button": "Send feedback",
        "support_email_label": "Support email",
        "quick_label": "Quick feedback",
        "detailed_label": "Detailed report",
        "video_tab": "Shot video",
        "pose_tab": "Release pose",
        "empty_pose": "Run analysis to generate the annotated release pose.",
        "waiting": "Upload a video to begin.",
        "spinner": "Analyzing mechanics and preparing report notes...",
        "done": "Analysis complete.",
        "analysis_error": "Motion analysis failed.",
        "result_missing": "Analysis did not produce a valid result file.",
        "result_invalid": "The result file is incomplete or unreadable.",
        "analysis_timeout": "Analysis took too long and was stopped.",
        "quality_title": "This video could not be analyzed reliably.",
        "not_shot_title": "This does not look like a basketball shooting clip.",
        "not_shot_guidance": "Please upload one clear basketball shot. The player should raise the shooting hand above the shoulder/head and complete the release and follow-through in frame.",
        "quality_guidance": """
Please upload a short, clear shooting clip:
- 3-8 seconds, no edits, cuts, or slow-motion effects
- Full body visible from feet to shooting hand throughout the shot
- Side view or 45-degree angle, with only one main shooter in frame
- Good lighting, steady camera, and at least 720p resolution
- Include the full motion: dip/load, jump or extension, release, and follow-through
""",
        "limited_title": "Limited video analysis",
        "limited_guidance": "The app could not extract reliable body landmarks from this clip, so exact angle metrics are unavailable. It will still provide basic report notes. A clearer full-body side-view video can unlock more detailed biomechanics.",
        "debug_details": "Analysis diagnostics",
        "timing_warning": "The pose was detected, but the loading-to-release timing may be unreliable for this clip. The report will focus more on visible posture metrics.",
        "coach_error": "Report notes returned an error:",
        "coach_timeout": "Report notes timed out. Please retry later or use quick feedback.",
        "score_title": "Form score",
        "score_label": "Shot mechanics",
        "score_caption": "A form-quality score for balance, timing, and repeatability. It is not a make-percentage prediction.",
        "metrics_title": "Key biomechanics",
        "stability_title": "Shot consistency",
        "stability_score": "Consistency score",
        "stability_detected": "Detected shots",
        "stability_confidence": "Confidence",
        "stability_low": "Low",
        "stability_medium": "Medium",
        "stability_high": "High",
        "stability_limited": "Upload 5 or more shots for a more reliable consistency read. This result is still useful for a first look.",
        "stability_merge_warning": "These shots may not share the same player, camera angle, or distance. Consistency results may be less reliable.",
        "stability_help": "This section compares repeated releases in the same clip. More shots make the pattern more trustworthy.",
        "coach_title": "Report notes and drills",
        "no_feedback": "No report notes were returned.",
        "metric_elbow": "Elbow angle",
        "metric_elbow_help": "Release-arm extension at the moment of release.",
        "metric_height": "Release height",
        "metric_height_help": "Wrist height relative to the head; higher positive values mean a higher release.",
        "metric_lean": "Body lean",
        "metric_lean_help": "Horizontal shoulder-to-hip offset; closer to zero is usually steadier.",
        "metric_dip_knee": "Dip knee angle",
        "metric_dip_knee_help": "Knee angle at the lowest loading point.",
        "metric_release_knee": "Release knee angle",
        "metric_release_knee_help": "Knee angle when the shot is released.",
        "metric_extension": "Knee extension",
        "metric_extension_help": "How much the knees extend from dip to release.",
        "metric_flow": "Power-to-release frames",
        "metric_flow_help": "Frames between lowest dip and release; very high values can suggest a pause.",
        "styles": {
            "general": "General mechanics",
            "curry": "Stephen Curry",
            "durant": "Kevin Durant",
            "thompson": "Klay Thompson",
        },
    },
    "de": {
        "page_title": "Basketball Wurf-Check",
        "eyebrow": "Video-Wurfbericht",
        "title": "Basketball Wurf-Check",
        "desc": "Lade einen oder mehrere Wurfclips hoch und erhalte einen strukturierten Technikbericht zu Release, Mechanik, Stabilität und konkreten Übungen.",
        "language": "Sprache",
        "settings": "Analyse starten",
        "style_label": "Referenzstil",
        "mode_label": "Berichtsart",
        "source_label": "Videoquelle",
        "source_record": "Mit dem Handy aufnehmen",
        "source_upload": "Vorhandenes Video hochladen",
        "upload_label": "Wurfvideo hochladen",
        "record_upload_label": "Wurfvideo aufnehmen oder auswählen",
        "record_hint": "Ein Clip darf Wurf, Ball holen, Dribbling, Gehen und den nächsten Wurf enthalten. Die Person sollte zwischen den Würfen sichtbar bleiben.",
        "upload_help": "Der Button kann weiterhin Upload heißen. Am Handy öffnet er Kamera oder Foto-/Videomediathek.",
        "record_checklist_title": "Vor dem Aufnehmen kurz prüfen:",
        "record_checklist": """
- Am besten 5 oder mehr Würfe in einem Clip filmen
- Weniger Würfe funktionieren auch, aber die Stabilitätsanalyse ist dann unsicherer
- Ball holen, Dribbling oder Gehen zwischen den Würfen ist okay
- Für die Stabilitätsanalyse gleiche Person, gleiche Perspektive und ähnliche Distanz nutzen
- Querformat oder Hochformat ist okay, aber der ganze Körper muss sichtbar bleiben
- Kamera etwa 2-4 Meter entfernt platzieren
- Beste Perspektive: Seitenansicht oder etwa 45 Grad
- Füße, Knie, Wurfhand und Follow-through bleiben im Bild
- Gute Beleuchtung, ruhiges Handy, keine Zeitlupe oder Schnitte
- Wenn der Upload nicht klappt: kürzer filmen und 1080p statt 4K/HDR nutzen
""",
        "api_settings": "AI API Einstellungen",
        "api_settings_help": "Nur für lokale Tests. Keys werden nicht im Code gespeichert.",
        "provider_label": "AI Dienst",
        "provider_auto": "Automatisch",
        "provider_openai": "OpenAI",
        "provider_gemini": "Gemini",
        "openai_key_label": "OpenAI API key",
        "gemini_key_label": "Gemini API key",
        "model_label": "Modell überschreiben (optional)",
        "missing_key": "Bitte zuerst einen API key konfigurieren, um Berichtshinweise zu erzeugen.",
        "file_too_large": "Dieses Video ist zu groß. Bitte lade maximal {max_mb} MB hoch. Wenn du am Handy filmst, nutze einen kürzeren Clip oder 1080p statt 4K/HDR.",
        "unsupported_file": "Bitte wähle eine Videodatei aus. Fotos oder nicht unterstützte Dateien können nicht analysiert werden.",
        "upload_summary": "{count} Video(s) ausgewählt.",
        "cooldown": "Bitte warte noch {seconds} Sekunden, bevor du die nächste Analyse startest.",
        "start_label": "Analyse starten",
        "payment_required_title": "Schritt 1: Beta-Bericht kaufen",
        "payment_required_body": "Bezahle zuerst sicher über Stripe. Nach dem Checkout kommst du hierher zurück, lädst dein Video hoch und erstellst den Bericht.",
        "payment_button_label": "1,99 Euro mit Stripe bezahlen",
        "payment_pending": "Vor Upload und Berichtserstellung ist die Zahlung erforderlich. Kehre nach dem Checkout über den Erfolgslink zurück, um den Upload-Bereich freizuschalten.",
        "payment_unlocked": "Zahlungsrückkehr erkannt. Du kannst dein Video jetzt hochladen und den Bericht erstellen.",
        "payment_config_missing": "Zahlung ist aktiviert, aber PAYMENT_ACCESS_TOKEN fehlt. Bitte in Streamlit Secrets ergänzen und in Stripe als Erfolgslink hinterlegen.",
        "payment_link_missing": "Der Zahlungslink ist noch nicht konfiguriert. Die Analyse bleibt deshalb zum Testen offen.",
        "download_report": "Bericht als PDF herunterladen",
        "support_title": "Feedback, Problem oder Rückerstattung",
        "support_body": "Wenn der Bericht fehlschlägt, unpassend wirkt oder du eine Rückerstattung möchtest, kontaktiere uns mit Zahlungs-E-Mail und kurzer Beschreibung.",
        "support_button": "Feedback senden",
        "support_email_label": "Support-E-Mail",
        "quick_label": "Kurzfeedback",
        "detailed_label": "Detailbericht",
        "video_tab": "Wurfvideo",
        "pose_tab": "Release-Pose",
        "empty_pose": "Starte die Analyse, um die markierte Release-Pose zu erzeugen.",
        "waiting": "Lade ein Video hoch, um zu beginnen.",
        "spinner": "Analysiere Wurfmechanik und erstelle Berichtshinweise...",
        "done": "Analyse abgeschlossen.",
        "analysis_error": "Bewegungsanalyse fehlgeschlagen.",
        "result_missing": "Die Analyse hat keine gültige Ergebnisdatei erzeugt.",
        "result_invalid": "Die Ergebnisdatei ist unvollständig oder nicht lesbar.",
        "analysis_timeout": "Die Analyse hat zu lange gedauert und wurde gestoppt.",
        "quality_title": "Dieses Video konnte nicht zuverlässig analysiert werden.",
        "not_shot_title": "Das sieht nicht wie ein Basketball-Wurfclip aus.",
        "not_shot_guidance": "Bitte lade einen klaren Basketballwurf hoch. Die Wurfhand sollte über Schulter/Kopf geführt werden, mit Release und Follow-through im Bild.",
        "quality_guidance": """
Bitte lade einen kurzen, klaren Wurfclip hoch:
- 3-8 Sekunden, ohne Schnitte, Übergänge oder Zeitlupe
- Der ganze Körper ist vom Fuß bis zur Wurfhand sichtbar
- Seitenansicht oder 45-Grad-Winkel, möglichst nur eine Person im Bild
- Gute Beleuchtung, ruhige Kamera, idealerweise mindestens 720p
- Vollständige Bewegung: Dip/Load, Streckung, Release und Follow-through
""",
        "limited_title": "Eingeschränkte Videoanalyse",
        "limited_guidance": "Das System konnte aus diesem Clip keine stabilen Körperpunkte extrahieren. Exakte Winkelwerte werden deshalb nicht angezeigt, aber du erhältst trotzdem grundlegende Berichtshinweise. Ein klareres Ganzkörpervideo von der Seite ermöglicht detailliertere Biomechanik.",
        "debug_details": "Analyse-Diagnose",
        "timing_warning": "Die Pose wurde erkannt, aber der Timing-Wert vom Load bis zum Release ist bei diesem Clip möglicherweise unzuverlässig.",
        "coach_error": "Berichtshinweise haben einen Fehler zurückgegeben:",
        "coach_timeout": "Berichtshinweise haben zu lange gedauert. Bitte später erneut versuchen oder Kurzfeedback nutzen.",
        "score_title": "Form-Score",
        "score_label": "Wurfmechanik",
        "score_caption": "Ein Qualitätswert für Balance, Timing und Wiederholbarkeit. Er ist keine Trefferwahrscheinlichkeit.",
        "metrics_title": "Wichtige Biomechanik",
        "stability_title": "Wurfstabilität",
        "stability_score": "Stabilitätswert",
        "stability_detected": "Erkannte Würfe",
        "stability_confidence": "Verlässlichkeit",
        "stability_low": "Niedrig",
        "stability_medium": "Mittel",
        "stability_high": "Hoch",
        "stability_limited": "Lade 5 oder mehr Würfe hoch, um die Stabilität zuverlässiger einzuschätzen. Dieses Ergebnis ist trotzdem als erster Check nutzbar.",
        "stability_merge_warning": "Diese Würfe wirken möglicherweise nicht wie gleiche Person, gleicher Kamerawinkel oder gleiche Distanz. Die Stabilitätswerte können dadurch unzuverlässiger sein.",
        "stability_help": "Dieser Bereich vergleicht wiederholte Releases im selben Clip. Mehr Würfe machen das Muster verlässlicher.",
        "coach_title": "Berichtshinweise und Übungen",
        "no_feedback": "Es wurden keine Berichtshinweise zurückgegeben.",
        "metric_elbow": "Ellbogenwinkel",
        "metric_elbow_help": "Streckung des Wurfarms im Moment des Releases.",
        "metric_height": "Release-Höhe",
        "metric_height_help": "Höhe des Handgelenks relativ zum Kopf; höhere positive Werte bedeuten einen höheren Release.",
        "metric_lean": "Körperneigung",
        "metric_lean_help": "Horizontaler Versatz zwischen Schulter und Hüfte; näher an 0 ist meist stabiler.",
        "metric_dip_knee": "Kniewinkel im Dip",
        "metric_dip_knee_help": "Kniewinkel am tiefsten Ladepunkt.",
        "metric_release_knee": "Kniewinkel beim Release",
        "metric_release_knee_help": "Kniewinkel im Moment des Releases.",
        "metric_extension": "Kniestreckung",
        "metric_extension_help": "Wie stark die Knie vom Dip bis zum Release strecken.",
        "metric_flow": "Frames Load-zu-Release",
        "metric_flow_help": "Frames zwischen tiefstem Dip und Release; sehr hohe Werte können auf eine Pause hindeuten.",
        "styles": {
            "general": "Allgemeine Wurfmechanik",
            "curry": "Stephen Curry",
            "durant": "Kevin Durant",
            "thompson": "Klay Thompson",
        },
    },
    "zh": {
        "page_title": "篮球投篮动作体检",
        "eyebrow": "视频投篮报告",
        "title": "篮球投篮动作体检",
        "desc": "上传一段或多段投篮视频，获得结构化动作报告：出手姿态、关键指标、投篮稳定性和下一步训练建议。",
        "language": "语言",
        "settings": "本次分析设置",
        "style_label": "对标风格",
        "mode_label": "点评模式",
        "source_label": "视频来源",
        "source_record": "用手机现场拍摄",
        "source_upload": "上传已有视频",
        "upload_label": "上传投篮视频",
        "record_upload_label": "拍摄或选择投篮视频",
        "record_hint": "一个视频里可以包含投篮、捡球、运球、走动和下一次投篮；两次投篮之间尽量保持球员可见。",
        "upload_help": "按钮可能仍显示 Upload，这是手机浏览器打开相机或照片/视频库的入口。",
        "record_checklist_title": "拍摄前请确认：",
        "record_checklist": """
- 最好在同一段视频里拍 5 次或更多投篮
- 少于 5 次也可以分析，但稳定性判断会更不确定
- 投篮之间捡球、运球、走动都可以
- 稳定性分析请尽量保持同一球员、同一角度和相似距离
- 横屏或竖屏都可以，但全身必须始终可见
- 手机距离人大约 2-4 米
- 最佳角度：侧面或约 45 度
- 脚、膝盖、投篮手和随球动作都在画面里
- 光线充足、手机稳定，不要慢动作或剪辑
- 如果无法上传，请缩短视频，使用 1080p 而不是 4K/HDR
""",
        "api_settings": "AI API 设置",
        "api_settings_help": "仅用于本地测试。Key 只在本次会话中使用，不会保存到代码里。",
        "provider_label": "AI 服务",
        "provider_auto": "自动选择",
        "provider_openai": "OpenAI",
        "provider_gemini": "Gemini",
        "openai_key_label": "OpenAI API key",
        "gemini_key_label": "Gemini API key",
        "model_label": "模型覆盖（可选）",
        "missing_key": "请先在 API 设置中填写 key，再生成报告解读。",
        "file_too_large": "这个视频文件太大。请上传不超过 {max_mb} MB 的视频。如果用手机拍摄，请缩短视频，或使用 1080p 而不是 4K/HDR。",
        "unsupported_file": "请选择视频文件。照片或不支持的文件无法分析。",
        "upload_summary": "已选择 {count} 个视频。",
        "cooldown": "请再等待 {seconds} 秒后开始下一次分析。",
        "start_label": "开始分析",
        "payment_required_title": "第一步：购买 Beta 报告",
        "payment_required_body": "请先通过 Stripe 安全付款。付款后会回到这里，再上传视频并生成报告。",
        "payment_button_label": "通过 Stripe 支付 1.99 欧元",
        "payment_pending": "上传和生成报告前需要先完成付款。付款后请通过支付成功页面返回，系统会解锁上传区。",
        "payment_unlocked": "已检测到付款返回链接，现在可以上传视频并生成报告。",
        "payment_config_missing": "已启用付款，但缺少 PAYMENT_ACCESS_TOKEN。请在 Streamlit Secrets 中添加，并在 Stripe 成功返回链接中使用。",
        "payment_link_missing": "付款链接尚未配置，所以当前仍开放测试分析。",
        "download_report": "下载 PDF 报告",
        "support_title": "反馈、问题或退款申请",
        "support_body": "如果报告失败、结果明显不满意，或你想申请退款，请附上付款邮箱和简短说明联系我们。",
        "support_button": "提交反馈",
        "support_email_label": "客服邮箱",
        "quick_label": "快速点评",
        "detailed_label": "深度报告",
        "video_tab": "投篮视频",
        "pose_tab": "出手姿态",
        "empty_pose": "完成分析后会生成带关键点的出手姿态图。",
        "waiting": "先上传一段视频开始分析。",
        "spinner": "正在分析投篮动作并生成报告解读...",
        "done": "分析完成！",
        "analysis_error": "动作分析失败。",
        "result_missing": "分析没有生成有效的结果文件。",
        "result_invalid": "结果文件不完整或无法读取。",
        "analysis_timeout": "分析时间过长，已停止处理。",
        "quality_title": "这段视频无法被稳定分析。",
        "not_shot_title": "这看起来不像篮球投篮视频。",
        "not_shot_guidance": "请上传一段清楚的篮球投篮视频：投篮手需要举到肩膀/头部以上，并在画面中完成出手和随球动作。",
        "quality_guidance": """
请上传一段更适合动作识别的投篮视频：
- 时长 3-8 秒，不要剪辑、转场或慢动作特效
- 从脚到投篮手全身始终清楚可见
- 侧面或 45 度角拍摄，画面里尽量只有一个主要投篮人
- 光线充足、镜头稳定，建议至少 720p
- 包含完整动作：下蹲蓄力、起跳或伸展、出手、随球动作
""",
        "limited_title": "基础视频分析",
        "limited_guidance": "系统暂时无法从这段视频中稳定提取人体关键点，所以不会显示精确角度指标。但仍会给出基础报告解读；如果上传更清楚的侧面全身视频，可以获得更详细的生物力学分析。",
        "debug_details": "分析诊断信息",
        "timing_warning": "系统已识别到人体姿态，但这段视频的“蓄力到出手节奏”指标可能不稳定。本次报告会更多参考可见姿态指标。",
        "coach_error": "报告解读生成失败：",
        "coach_timeout": "报告解读响应超时。可以稍后重试，或改用快速点评。",
        "score_title": "综合评分",
        "score_label": "投篮动作",
        "score_caption": "这是关于平衡、节奏和可重复性的动作质量评分，不代表这次投篮的命中率。",
        "metrics_title": "关键生物力学指标",
        "stability_title": "投篮稳定性",
        "stability_score": "稳定性评分",
        "stability_detected": "识别到的投篮次数",
        "stability_confidence": "判断可信度",
        "stability_low": "低",
        "stability_medium": "中",
        "stability_high": "高",
        "stability_limited": "上传 5 次或更多投篮可以获得更可靠的稳定性判断；当前结果仍可作为初步参考。",
        "stability_merge_warning": "这些投篮可能不是同一球员、同一拍摄角度或相似距离，稳定性结果会更不可靠。",
        "stability_help": "这一单元会比较同一段视频里的多次出手。投篮次数越多，动作模式越可信。",
        "coach_title": "报告解读与训练建议",
        "no_feedback": "没有返回报告解读。",
        "metric_elbow": "手肘角度",
        "metric_elbow_help": "出手瞬间投篮手臂的伸展程度。",
        "metric_height": "出手高度",
        "metric_height_help": "手腕相对头部的高度；正值越大代表出手点越高。",
        "metric_lean": "身体前倾",
        "metric_lean_help": "肩膀相对髋部的水平偏移；越接近 0 通常越稳定。",
        "metric_dip_knee": "最低点膝盖角度",
        "metric_dip_knee_help": "下蹲蓄力最低点的膝盖角度。",
        "metric_release_knee": "出手时膝盖角度",
        "metric_release_knee_help": "出手瞬间的膝盖伸展角度。",
        "metric_extension": "膝盖伸展幅度",
        "metric_extension_help": "从下蹲到出手阶段膝盖伸展了多少。",
        "metric_flow": "发力到出手帧数",
        "metric_flow_help": "从最低点到出手的帧数；过大可能代表停顿或分段发力。",
        "styles": {
            "general": "通用标准投篮",
            "curry": "Stephen Curry",
            "durant": "Kevin Durant",
            "thompson": "Klay Thompson",
        },
    },
}

LANDING = {
    "de": {
        "headline": "Basketball Wurf-Check ab 1,99 Euro testen",
        "subhead": "Ein schneller Technikbericht aus deinem Wurfvideo: Release-Pose, Messwerte, Stabilität über mehrere Würfe und ein klarer Trainingsfokus.",
        "cta": "Video hochladen",
        "price": "Beta-Test: 1,99 Euro pro Basisbericht geplant",
        "proof": "Für Spieler, Eltern und Coaches, die schnell wissen wollen: Was macht meinen Wurf unkonstant?",
        "badges": ["Kein Abo", "5+ Würfe empfohlen", "Auch mit 1 Clip nutzbar"],
        "steps_title": "So funktioniert der Test",
        "steps": [
            ("1. Filmen", "Nimm 1 bis 5+ Würfe auf. Mehr Würfe machen die Stabilitätsanalyse deutlich stärker."),
            ("2. Hochladen", "Das Video bleibt kurz und einfach: ganzer Körper sichtbar, gute Beleuchtung, keine Zeitlupe."),
            ("3. Bericht lesen", "Du bekommst Score, Release-Pose, wichtigste Messwerte, Stabilität und den nächsten Übungsfokus."),
        ],
        "cards": [
            ("Was du bekommst", "Form-Score, Release-Pose, Ellbogenwinkel, Kniewinkel, Körperneigung und Stabilitätswerte."),
            ("Wofür es gedacht ist", "Ein schneller Check für Sprungwurf, Freiwurf oder Catch-and-Shoot Technik."),
            ("Was es nicht ersetzt", "Keinen echten Coach. Es ist ein strukturierter Erstcheck, der bessere Fragen und gezieltere Übungen ermöglicht."),
        ],
        "sample_title": "Beispielbericht ansehen",
        "sample_score": "Form-Score: 88/100",
        "sample_metrics": [
            "Ellbogenwinkel: 150 Grad",
            "Kniewinkel beim Release: 153 Grad",
            "Kniestreckung: 57 Grad",
            "Körperneigung: stabil",
        ],
        "sample_feedback": [
            "Starker Pluspunkt: guter Release und stabile Balance.",
            "Wichtigster Fokus: den Oberkörper beim Hochgehen noch ruhiger halten.",
            "Übung: 25 einhändige Formwürfe nah am Korb, danach 25 Catch-and-Shoot Würfe aus der Mitteldistanz.",
        ],
        "questions_title": "Häufige Fragen, die der Bericht beantworten soll",
        "questions": [
            "Warum ist mein Wurf jeden Tag anders?",
            "Warum verfehle ich oft links oder rechts?",
            "Stört meine Guide Hand den Release?",
            "Nutze ich genug Beine oder zu viel Oberkörper?",
            "Welche eine Sache sollte ich zuerst verbessern?",
        ],
        "report_title": "So sieht ein Basisbericht aus",
        "report_summary": "Ein guter Report soll nicht zehn Baustellen öffnen, sondern die wichtigste Verbesserung klar priorisieren.",
        "report_sections": [
            ("1. Score", "88/100 - starke Grundmechanik, gute Balance, aber Timing vom Load bis zum Release noch etwas lang."),
            ("2. Wichtigste Messwerte", "Ellbogenwinkel 150 Grad, Kniestreckung 57 Grad, Körperneigung stabil."),
            ("3. Priorität", "Oberkörper beim Hochgehen ruhiger halten, damit der Release noch wiederholbarer wird."),
            ("4. Übungen", "25 einhändige Formwürfe nah am Korb, danach 25 Catch-and-Shoot Würfe aus der Mitteldistanz."),
        ],
        "sample_image_caption": "Beispiel einer markierten Release-Pose",
        "trust_title": "Ehrliche Grenzen",
        "trust_items": [
            "Der Bericht bewertet sichtbare Technik, nicht ob ein einzelner Wurf getroffen wurde.",
            "Schlechte Videos liefern weniger Details, aber können trotzdem für einen ersten Hinweis reichen.",
            "Frontale Clips sind möglich; Seitenansicht oder 45 Grad bleibt für Biomechanik am besten.",
        ],
        "payment_submit": "Beta-Bericht kaufen",
        "payment_hint": "Öffnet den sicheren Stripe-Bezahlvorgang in einem neuen Tab.",
        "payment_note": "Nach der Zahlung kommst du zurück und kannst dein Wurfvideo hochladen.",
    },
    "en": {
        "headline": "Test a basketball shot form check from 1.99 Euro",
        "subhead": "A quick technique report from your shooting video: release pose, mechanics, consistency across repeated shots, and one clear training focus.",
        "cta": "Upload video",
        "price": "Beta test: planned 1.99 Euro per basic report",
        "proof": "For players, parents, and coaches who want to know what makes a shot inconsistent.",
        "badges": ["No subscription", "5+ shots recommended", "Works with one clip"],
        "steps_title": "How the test works",
        "steps": [
            ("1. Film", "Record 1 to 5+ shots. More shots make the consistency section much stronger."),
            ("2. Upload", "Keep the video simple: full body visible, good light, no slow motion."),
            ("3. Read report", "Get score, release pose, key metrics, consistency, and the next drill focus."),
        ],
        "cards": [
            ("What you get", "Form score, release pose, elbow angle, knee angles, body lean, and consistency metrics."),
            ("Best use case", "A fast check for jump shots, free throws, or catch-and-shoot mechanics."),
            ("What it does not replace", "A real coach. It is a structured first pass that helps you ask better questions and train more deliberately."),
        ],
        "sample_title": "View sample report",
        "sample_score": "Form score: 88/100",
        "sample_metrics": [
            "Elbow angle: 150 degrees",
            "Release knee angle: 153 degrees",
            "Knee extension: 57 degrees",
            "Body lean: stable",
        ],
        "sample_feedback": [
            "Main strength: solid release and stable balance.",
            "Top focus: keep the torso quieter through the upward motion.",
            "Drill: 25 one-hand form shots close to the rim, then 25 catch-and-shoot midrange shots.",
        ],
        "questions_title": "Common questions the report should answer",
        "questions": [
            "Why does my shot change every day?",
            "Why do I miss left or right?",
            "Is my guide hand affecting the release?",
            "Am I using my legs enough?",
            "What is the first thing I should improve?",
        ],
        "report_title": "What a basic report looks like",
        "report_summary": "A useful report should not create ten problems. It should prioritize the next improvement clearly.",
        "report_sections": [
            ("1. Score", "88/100 - strong basic mechanics and balance, with load-to-release timing still a little long."),
            ("2. Key metrics", "Elbow angle 150 degrees, knee extension 57 degrees, body lean stable."),
            ("3. Priority", "Keep the torso quieter on the way up so the release becomes more repeatable."),
            ("4. Drills", "25 one-hand form shots close to the rim, then 25 catch-and-shoot midrange shots."),
        ],
        "sample_image_caption": "Example annotated release pose",
        "trust_title": "Honest limits",
        "trust_items": [
            "The report evaluates visible mechanics, not whether one shot made or missed.",
            "Lower-quality videos return fewer details, but can still give a first signal.",
            "Front-view clips can work; side view or 45 degrees is still best for biomechanics.",
        ],
        "payment_submit": "Buy beta report",
        "payment_hint": "Opens the secure Stripe checkout in a new tab.",
        "payment_note": "After payment, return here and upload your shooting video.",
    },
    "zh": {
        "headline": "测试 1.99 欧元篮球投篮动作报告",
        "subhead": "从你的投篮视频生成一份快速技术报告：出手姿态、动作指标、多次投篮稳定性，以及一个最优先训练重点。",
        "cta": "上传视频",
        "price": "Beta 测试：计划基础报告每份 1.99 欧元",
        "proof": "适合想快速知道“为什么投篮不稳定”的球员、家长和教练。",
        "badges": ["无需订阅", "建议 5 次以上投篮", "一个视频也可分析"],
        "steps_title": "测试流程",
        "steps": [
            ("1. 拍摄", "拍 1 到 5 次以上投篮。投篮次数越多，稳定性分析越有价值。"),
            ("2. 上传", "视频尽量简单：全身可见、光线清楚、不要慢动作。"),
            ("3. 看报告", "获得评分、出手姿态、关键指标、稳定性和下一步训练重点。"),
        ],
        "cards": [
            ("你会得到什么", "动作评分、出手姿态图、手肘角度、膝盖角度、身体前倾和稳定性指标。"),
            ("适合什么场景", "快速检查跳投、罚球或接球投的基础动作。"),
            ("它不能替代什么", "它不能替代真人教练，而是一个结构化初筛，帮你更清楚地提问和训练。"),
        ],
        "sample_title": "查看样例报告",
        "sample_score": "动作评分：88/100",
        "sample_metrics": [
            "手肘角度：150 度",
            "出手膝盖角度：153 度",
            "膝盖伸展：57 度",
            "身体前倾：稳定",
        ],
        "sample_feedback": [
            "主要优点：出手稳定，平衡不错。",
            "优先改进：向上发力时让上半身更安静。",
            "训练建议：近筐单手定型投 25 个，再做中距离接球投 25 个。",
        ],
        "questions_title": "报告应该回答的常见问题",
        "questions": [
            "为什么我的投篮每天都不一样？",
            "为什么总是偏左或偏右？",
            "我的辅助手是否影响出手？",
            "我是否用了足够的腿部力量？",
            "我最应该先改哪一个问题？",
        ],
        "report_title": "基础报告示例",
        "report_summary": "好的报告不应该一次制造十个问题，而是清楚指出下一步最该改什么。",
        "report_sections": [
            ("1. 评分", "88/100 - 基础动作和平衡较好，但蓄力到出手节奏仍有一点偏长。"),
            ("2. 关键指标", "手肘角度 150 度，膝盖伸展 57 度，身体前倾稳定。"),
            ("3. 优先级", "向上发力时保持上半身更安静，让出手更可重复。"),
            ("4. 训练", "近筐单手定型投 25 个，再做中距离接球投 25 个。"),
        ],
        "sample_image_caption": "出手姿态标注示例",
        "trust_title": "诚实的边界",
        "trust_items": [
            "报告评估可见动作，不判断某一次投篮是否命中。",
            "视频质量较低时会减少细节，但仍可给出初步方向。",
            "正面视频也可以尝试；侧面或 45 度角仍然最适合生物力学分析。",
        ],
        "payment_submit": "购买 Beta 报告",
        "payment_hint": "会在新标签页打开安全的 Stripe 支付页面。",
        "payment_note": "付款后回到这里上传你的投篮视频。",
    },
}


def get_secret(name, default=""):
    if os.getenv(name):
        return os.getenv(name, default)

    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def get_int_secret(name, default, min_value=None, max_value=None):
    raw_value = get_secret(name, str(default))
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        value = default

    if min_value is not None:
        value = max(min_value, value)
    if max_value is not None:
        value = min(max_value, value)
    return value


def clean_external_url(url):
    url = (url or "").strip()
    if not url:
        return ""
    if url.startswith(("http://", "https://", "mailto:")):
        return url
    return f"https://{url}"


def get_query_param(name):
    value = st.query_params.get(name, "")
    if isinstance(value, list):
        return value[0] if value else ""
    return value or ""


def clean_report_notes(output):
    lines = []
    for line in (output or "").splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append("")
            continue
        lowered = stripped.lower()
        if lowered.startswith("generating ai coach") or lowered.startswith("erstelle ai coach") or "正在生成 ai 教练" in lowered:
            continue
        if stripped.startswith("=====") and ("AI Coach" in stripped or "AI教练" in stripped):
            continue
        cleaned = (
            line.replace("AI Coach-Feedback", "Berichtshinweise")
            .replace("AI Coach Feedback", "Report notes")
            .replace("AI coach feedback", "report notes")
            .replace("AI Coach", "Report")
            .replace("AI教练点评", "报告解读")
            .replace("AI 教练点评", "报告解读")
            .replace("AI教练", "报告")
        )
        lines.append(cleaned)
    return "\n".join(lines).strip()


def build_report_markdown(metrics, score, stability, feedback, fallback_analysis):
    lines = [f"# {t['title']}", ""]
    if fallback_analysis:
        lines.extend([f"## {t['limited_title']}", t["limited_guidance"], ""])
    else:
        lines.extend(
            [
                f"## {t['score_title']}",
                f"{t['score_label']}: {score}/100",
                t["score_caption"],
                "",
                f"## {t['metrics_title']}",
                f"- {t['metric_elbow']}: {metrics['elbow_angle']:.1f} deg",
                f"- {t['metric_height']}: {metrics['release_height']:.1f} px",
                f"- {t['metric_lean']}: {metrics['body_lean']:.1f} px",
                f"- {t['metric_dip_knee']}: {metrics['dip_knee_angle']:.1f} deg",
                f"- {t['metric_release_knee']}: {metrics['release_knee_angle']:.1f} deg",
                f"- {t['metric_extension']}: {metrics['knee_extension']:.1f} deg",
                f"- {t['metric_flow']}: {metrics['flow_frames']:.0f}",
                "",
            ]
        )

    if stability:
        confidence_labels = {
            "low": t["stability_low"],
            "medium": t["stability_medium"],
            "high": t["stability_high"],
        }
        lines.extend(
            [
                f"## {t['stability_title']}",
                f"- {t['stability_detected']}: {stability.get('detected_shots', 0)}/{stability.get('recommended_shots', 5)}+",
                f"- {t['stability_score']}: {stability.get('stability_score', 'N/A')}/100",
                f"- {t['stability_confidence']}: {confidence_labels.get(stability.get('confidence', 'low'), stability.get('confidence', 'low'))}",
                "",
            ]
        )

    if feedback:
        lines.extend([f"## {t['coach_title']}", feedback, ""])
    return "\n".join(lines).strip()


def make_pdf_report(report_text, analyzed_image_bytes=None):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Image as PdfImage
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    font_name = "Helvetica"
    for font_path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]:
        if Path(font_path).exists():
            font_name = "ReportFont"
            pdfmetrics.registerFont(TTFont(font_name, font_path))
            break

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=t["title"],
    )
    base_styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=base_styles["Title"],
        fontName=font_name,
        fontSize=22,
        leading=27,
        textColor=colors.HexColor("#111827"),
        spaceAfter=10,
        wordWrap="CJK",
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=base_styles["BodyText"],
        fontName=font_name,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#4b5563"),
        spaceAfter=14,
        wordWrap="CJK",
    )
    heading_style = ParagraphStyle(
        "ReportHeading",
        parent=base_styles["Heading2"],
        fontName=font_name,
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#ef4444"),
        spaceBefore=10,
        spaceAfter=6,
        wordWrap="CJK",
    )
    body_style = ParagraphStyle(
        "ReportBody",
        parent=base_styles["BodyText"],
        fontName=font_name,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#1f2937"),
        spaceAfter=5,
        wordWrap="CJK",
    )
    bullet_style = ParagraphStyle(
        "ReportBullet",
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-8,
        bulletIndent=0,
    )

    story = [
        Paragraph(escape(t["title"]), title_style),
        Paragraph(escape(t["score_caption"]), subtitle_style),
        Table(
            [[Paragraph(escape(t["score_title"]), body_style), Paragraph(escape(t["metrics_title"]), body_style), Paragraph(escape(t["stability_title"]), body_style)]],
            colWidths=[52 * mm, 52 * mm, 52 * mm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f3f4f6")),
                    ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#d1d5db")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 9),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ]
            ),
        ),
        Spacer(1, 10),
    ]

    if analyzed_image_bytes:
        try:
            image = Image.open(BytesIO(analyzed_image_bytes))
            image_width, image_height = image.size
            max_width = 160 * mm
            max_height = 85 * mm
            scale = min(max_width / image_width, max_height / image_height)
            story.extend(
                [
                    PdfImage(BytesIO(analyzed_image_bytes), width=image_width * scale, height=image_height * scale),
                    Spacer(1, 8),
                ]
            )
        except Exception:
            pass

    for raw_line in report_text.splitlines():
        line = raw_line.strip()
        if not line:
            story.append(Spacer(1, 4))
        elif line.startswith("#"):
            story.append(Paragraph(escape(line.lstrip("#").strip()), heading_style))
        elif line.startswith("- "):
            story.append(Paragraph(escape(line[2:]), bullet_style, bulletText="•"))
        else:
            story.append(Paragraph(escape(line), body_style))

    document.build(story)
    return buffer.getvalue()


def is_supported_video(uploaded_file):
    mime_type = (getattr(uploaded_file, "type", "") or "").lower()
    filename = (getattr(uploaded_file, "name", "") or "").lower()
    video_extensions = (".mp4", ".mov", ".m4v", ".mpeg4", ".webm", ".3gp", ".3gpp")
    return mime_type.startswith("video/") or filename.endswith(video_extensions)


def normalize_video_frame(frame, target_size):
    frame = np.asarray(frame)
    if frame.ndim == 2:
        frame = np.stack([frame] * 3, axis=-1)
    if frame.shape[2] == 4:
        frame = frame[:, :, :3]

    if target_size and (frame.shape[1], frame.shape[0]) != target_size:
        image = Image.fromarray(frame)
        image = image.resize(target_size, Image.Resampling.LANCZOS)
        frame = np.asarray(image)

    return frame


def combine_videos(video_paths, output_path, fps=25):
    target_size = None
    wrote_frame = False
    segments = []
    frame_index = 0

    with imageio.get_writer(str(output_path), fps=fps, codec="libx264", macro_block_size=16) as writer:
        for video_path in video_paths:
            segment_start = frame_index
            reader = imageio.get_reader(str(video_path))
            try:
                for frame in reader:
                    if target_size is None:
                        target_size = (frame.shape[1], frame.shape[0])
                    writer.append_data(normalize_video_frame(frame, target_size))
                    wrote_frame = True
                    frame_index += 1
            finally:
                reader.close()
            segments.append(
                {
                    "name": video_path.name,
                    "start_frame": segment_start,
                    "end_frame": frame_index,
                }
            )

    if not wrote_frame:
        raise ValueError("No frames were found in uploaded videos.")
    return segments


def calculate_score(metrics):
    score = 100
    elbow_angle = metrics["elbow_angle"]
    release_height = metrics["release_height"]
    body_lean = metrics["body_lean"]
    knee_extension = metrics["knee_extension"]
    flow_frames = metrics["flow_frames"]

    if elbow_angle < 150:
        score -= min(20, (150 - elbow_angle) * 0.8)
    elif elbow_angle > 175:
        score -= min(15, (elbow_angle - 175) * 0.8)

    if release_height < 0:
        score -= 20
    elif release_height < 20:
        score -= 10

    if abs(body_lean) > 40:
        score -= 15
    elif abs(body_lean) > 20:
        score -= 8

    if knee_extension < 30:
        score -= 15
    elif knee_extension < 50:
        score -= 8

    if flow_frames > 40:
        score -= 12
    elif flow_frames > 25:
        score -= 6
    elif flow_frames < 5:
        score -= 6

    return max(0, min(100, round(score)))


def load_metrics(result_path):
    if not result_path.exists():
        raise FileNotFoundError

    data = result_path.read_text(encoding="utf-8").strip().split(",")
    if len(data) != 7:
        raise ValueError

    values = [float(item) for item in data]
    return {
        "elbow_angle": values[0],
        "release_height": values[1],
        "body_lean": values[2],
        "dip_knee_angle": values[3],
        "release_knee_angle": values[4],
        "knee_extension": values[5],
        "flow_frames": values[6],
    }


def load_stability(stability_path):
    if not stability_path.exists():
        return None
    try:
        return json.loads(stability_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def timing_is_reliable(metrics):
    return metrics["flow_frames"] > 0


def show_video_quality_guidance():
    st.error(t["quality_title"])
    st.info(t["quality_guidance"])


def show_not_shot_guidance():
    st.error(t["not_shot_title"])
    st.info(t["not_shot_guidance"])


def show_limited_analysis_guidance():
    st.warning(t["limited_title"])
    st.info(t["limited_guidance"])


def show_debug_details(details):
    if (
        get_secret("SHOW_DEBUG_DETAILS", "false").lower() == "true"
        and get_secret("APP_ENV", "production").lower() == "development"
        and details
    ):
        with st.expander(t["debug_details"]):
            st.text(details[-2000:])


def clear_previous_analysis():
    for key in [
        "analyzed_image_bytes",
        "analysis_metrics",
        "analysis_score",
        "analysis_stability",
        "coach_feedback",
        "analysis_error_key",
    ]:
        st.session_state.pop(key, None)


def metric_card(label, value, help_text):
    st.metric(label, value)
    st.caption(help_text)


def render_stability(stability):
    if not stability:
        return

    confidence_labels = {
        "low": t["stability_low"],
        "medium": t["stability_medium"],
        "high": t["stability_high"],
    }
    detected_shots = int(stability.get("detected_shots") or 0)
    recommended_shots = int(stability.get("recommended_shots") or 5)
    confidence = stability.get("confidence", "low")
    score = stability.get("stability_score")

    st.subheader(t["stability_title"])
    st.caption(t["stability_help"])
    s1, s2, s3 = st.columns(3)
    with s1:
        st.metric(t["stability_detected"], f"{detected_shots}/{recommended_shots}+")
    with s2:
        st.metric(t["stability_score"], f"{score}/100" if score is not None else "N/A")
    with s3:
        st.metric(t["stability_confidence"], confidence_labels.get(confidence, confidence))

    if detected_shots < recommended_shots:
        st.info(t["stability_limited"])
    if stability.get("consistency_check", {}).get("warning"):
        st.warning(t["stability_merge_warning"])


def render_landing(lang_code, payment_url=""):
    landing = LANDING[lang_code]
    badge_html = "".join(f"<span>{badge}</span>" for badge in landing["badges"])
    st.markdown(
        f"""
        <section class="market-hero">
            <div class="market-copy">
                <div class="eyebrow">{t["eyebrow"]}</div>
                <h1>{landing["headline"]}</h1>
                <p>{landing["subhead"]}</p>
                <div class="market-badges">{badge_html}</div>
                <div class="market-price">{landing["price"]}</div>
                <div class="market-actions">
                    <a class="market-primary" href="#analysis-tool">{landing["cta"]}</a>
                </div>
                <div class="market-note">{landing["payment_note"]}</div>
                <div class="market-proof">{landing["proof"]}</div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(f"#### {landing['steps_title']}")
    step_cols = st.columns(3)
    for col, (title, body) in zip(step_cols, landing["steps"]):
        with col:
            st.markdown(
                f"""
                <div class="step-card">
                    <strong>{title}</strong>
                    <p>{body}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    card_cols = st.columns(3)
    for col, (title, body) in zip(card_cols, landing["cards"]):
        with col:
            st.markdown(
                f"""
                <div class="market-card">
                    <h3>{title}</h3>
                    <p>{body}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(f"#### {landing['report_title']}")
    st.caption(landing["report_summary"])
    report_cols = st.columns([0.7, 1.3], gap="large")
    with report_cols[0]:
        st.metric("Score", landing["sample_score"])
        for item in landing["sample_metrics"]:
            st.caption(item)
        sample_image_path = BASE_DIR / "release_analyzed.jpg"
        if sample_image_path.exists():
            st.image(str(sample_image_path), caption=landing["sample_image_caption"], use_container_width=True)
    with report_cols[1]:
        for title, body in landing["report_sections"]:
            st.markdown(
                f"""
                <div class="report-row">
                    <strong>{title}</strong>
                    <p>{body}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(f"#### {landing['trust_title']}")
    trust_cols = st.columns(3)
    for col, item in zip(trust_cols, landing["trust_items"]):
        with col:
            st.markdown(
                f"""
                <div class="trust-note">
                    {item}
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(f"#### {landing['questions_title']}")
    q_cols = st.columns([1, 1])
    for index, question in enumerate(landing["questions"]):
        with q_cols[index % 2]:
            st.markdown(f"- {question}")

    st.divider()
    st.markdown('<div id="analysis-tool"></div>', unsafe_allow_html=True)


def render_support_box(feedback_url, support_email):
    st.markdown(f"#### {t['support_title']}")
    st.caption(t["support_body"])
    support_cols = st.columns([1, 1], gap="small")
    with support_cols[0]:
        if feedback_url:
            st.link_button(t["support_button"], feedback_url, use_container_width=True)
    with support_cols[1]:
        if support_email:
            st.markdown(f"{t['support_email_label']}: [{support_email}](mailto:{support_email})")


st.set_page_config(
    page_title=TEXT["en"]["page_title"],
    page_icon="🏀",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.7rem;
        padding-bottom: 2.5rem;
        max-width: 1180px;
    }
    div[data-testid="stMetric"] {
        background: rgba(127, 127, 127, 0.10);
        border: 1px solid rgba(127, 127, 127, 0.26);
        border-radius: 8px;
        padding: 0.85rem 0.95rem;
        min-height: 110px;
    }
    div[data-testid="stMetricLabel"] {
        color: inherit;
        opacity: 0.78;
        font-weight: 650;
    }
    div[data-testid="stMetricValue"] {
        color: inherit;
        opacity: 1;
        font-weight: 800;
    }
    .hero {
        border-bottom: 1px solid rgba(127, 127, 127, 0.30);
        padding-bottom: 1rem;
        margin-bottom: 1.2rem;
    }
    .eyebrow {
        color: #b45309;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0;
        text-transform: uppercase;
        margin-bottom: 0.25rem;
    }
    .hero h1 {
        font-size: 2.2rem;
        line-height: 1.15;
        margin: 0;
    }
    .hero p {
        opacity: 0.76;
        max-width: 760px;
        margin-top: 0.55rem;
    }
    .score-note {
        opacity: 0.78;
        font-size: 0.9rem;
        margin-top: -0.35rem;
    }
    .market-hero {
        border: 1px solid rgba(127, 127, 127, 0.24);
        border-radius: 8px;
        padding: 1.35rem 1.45rem;
        margin-bottom: 1.15rem;
        background: rgba(127, 127, 127, 0.08);
    }
    .market-copy h1 {
        font-size: 2.45rem;
        line-height: 1.08;
        margin: 0;
        max-width: 900px;
    }
    .market-copy p {
        max-width: 820px;
        opacity: 0.82;
        margin: 0.7rem 0 0;
    }
    .market-badges {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin-top: 0.9rem;
    }
    .market-badges span {
        border: 1px solid rgba(127, 127, 127, 0.28);
        border-radius: 999px;
        padding: 0.28rem 0.58rem;
        font-size: 0.86rem;
        font-weight: 700;
        background: rgba(255, 255, 255, 0.04);
    }
    .market-price {
        display: inline-block;
        margin-top: 0.9rem;
        padding: 0.45rem 0.7rem;
        border: 1px solid rgba(59, 130, 246, 0.45);
        border-radius: 6px;
        color: #3b82f6;
        font-weight: 800;
    }
    .market-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 0.55rem;
        margin-top: 0.9rem;
    }
    .market-actions a {
        border-radius: 6px;
        padding: 0.55rem 0.82rem;
        font-weight: 800;
        text-decoration: none;
    }
    .market-primary {
        background: #ff4b4b;
        color: #ffffff !important;
    }
    .market-secondary {
        border: 1px solid rgba(127, 127, 127, 0.30);
        color: inherit !important;
        background: rgba(255, 255, 255, 0.04);
    }
    .market-proof {
        margin-top: 0.65rem;
        opacity: 0.74;
        font-size: 0.95rem;
    }
    .market-note {
        margin-top: 0.55rem;
        opacity: 0.72;
        font-size: 0.9rem;
    }
    .step-card {
        border: 1px solid rgba(59, 130, 246, 0.24);
        border-radius: 8px;
        padding: 0.95rem;
        min-height: 142px;
        background: rgba(59, 130, 246, 0.08);
        margin-bottom: 0.75rem;
    }
    .step-card strong {
        display: block;
        font-size: 1.02rem;
        margin-bottom: 0.4rem;
    }
    .step-card p {
        opacity: 0.80;
        margin: 0;
    }
    .market-card {
        border: 1px solid rgba(127, 127, 127, 0.24);
        border-radius: 8px;
        padding: 0.95rem;
        min-height: 145px;
        background: rgba(127, 127, 127, 0.07);
        margin-bottom: 0.5rem;
    }
    .market-card h3 {
        font-size: 1.05rem;
        margin: 0 0 0.45rem;
    }
    .market-card p {
        opacity: 0.78;
        margin: 0;
    }
    .report-row {
        border-left: 3px solid #ff4b4b;
        padding: 0.15rem 0 0.35rem 0.75rem;
        margin-bottom: 0.55rem;
    }
    .report-row p {
        margin: 0.2rem 0 0;
        opacity: 0.78;
    }
    .trust-note {
        border: 1px solid rgba(34, 197, 94, 0.22);
        border-radius: 8px;
        padding: 0.8rem 0.9rem;
        min-height: 96px;
        background: rgba(34, 197, 94, 0.07);
        color: inherit;
        opacity: 0.86;
        margin-bottom: 0.7rem;
    }
    @media (max-width: 640px) {
        .market-copy h1 {
            font-size: 2rem;
        }
        .hero h1 {
            font-size: 1.85rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

language_label = st.selectbox(
    "Language / 语言",
    list(LANG_OPTIONS.keys()),
    index=0,
)
lang_code = LANG_OPTIONS[language_label]
t = TEXT[lang_code]
max_upload_mb = get_int_secret("MAX_UPLOAD_MB", 180, 1, 500)
analysis_cooldown_seconds = get_int_secret("ANALYSIS_COOLDOWN_SECONDS", 20, 0, 300)
ai_max_output_tokens = get_int_secret("AI_COACH_MAX_OUTPUT_TOKENS", 650, 128, 1000)
payment_link_url = clean_external_url(get_secret("STRIPE_PAYMENT_LINK_URL", ""))
payment_access_token = get_secret("PAYMENT_ACCESS_TOKEN", "").strip()
feedback_form_url = clean_external_url(get_secret("FEEDBACK_FORM_URL", DEFAULT_FEEDBACK_URL))
support_email = get_secret("SUPPORT_EMAIL", "").strip()
payment_access = get_query_param("access").strip()
payment_unlocked = not payment_link_url or bool(payment_access_token and payment_access == payment_access_token)

render_landing(lang_code, payment_link_url)

st.markdown(
    f"""
    <div class="hero">
        <div class="eyebrow">{t["eyebrow"]}</div>
        <h1>{t["title"]}</h1>
        <p>{t["desc"]}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

settings_col, media_col = st.columns([0.92, 1.55], gap="large")
current_videos = st.session_state.get("uploaded_videos", [])
if payment_link_url and not payment_unlocked and current_videos:
    clear_previous_analysis()
    st.session_state.pop("uploaded_videos", None)
    current_videos = []

with settings_col:
    st.subheader(t["settings"])
    server_openai_key = get_secret("OPENAI_API_KEY")
    server_gemini_key = get_secret("GEMINI_API_KEY")
    server_provider = get_secret("AI_COACH_PROVIDER", "auto")
    server_model = get_secret("AI_COACH_MODEL")
    has_server_key = bool(server_openai_key or server_gemini_key)
    show_api_settings = get_secret("SHOW_API_SETTINGS", "false").lower() == "true" or not has_server_key

    player_model = st.selectbox(
        t["style_label"],
        ["general", "curry", "durant", "thompson"],
        format_func=lambda option: t["styles"][option],
    )
    mode = st.radio(
        t["mode_label"],
        ["quick", "detailed"],
        format_func=lambda option: t["quick_label"] if option == "quick" else t["detailed_label"],
        horizontal=True,
    )

    if payment_link_url and not payment_unlocked:
        st.markdown(f"#### {t['payment_required_title']}")
        if not payment_access_token:
            st.error(t["payment_config_missing"])
        else:
            st.caption(t["payment_required_body"])
            st.link_button(t["payment_button_label"], payment_link_url, type="primary", use_container_width=True)
            st.info(t["payment_pending"])
    else:
        if payment_link_url and payment_unlocked:
            st.success(t["payment_unlocked"])
        elif not payment_link_url:
            st.info(t["payment_link_missing"])

        st.info(f"**{t['record_checklist_title']}**\n{t['record_checklist']}")
        st.caption(t["record_hint"])

        upload_label = t["record_upload_label"]
        video = st.file_uploader(
            upload_label,
            type=["mp4", "mov", "m4v", "mpeg4", "webm", "3gp", "3gpp"],
            help=t["upload_help"],
            accept_multiple_files=True,
        )
        if video:
            unsupported_files = [item.name for item in video if not is_supported_video(item)]
            uploaded_videos = [
                {"name": item.name, "bytes": item.getvalue()}
                for item in video
                if is_supported_video(item)
            ]
            total_upload_bytes = sum(len(item["bytes"]) for item in uploaded_videos)
            max_upload_bytes = max_upload_mb * 1024 * 1024
            if unsupported_files:
                clear_previous_analysis()
                st.session_state.pop("uploaded_videos", None)
                current_videos = []
                st.error(t["unsupported_file"])
            elif total_upload_bytes > max_upload_bytes:
                clear_previous_analysis()
                st.session_state.pop("uploaded_videos", None)
                current_videos = []
                st.error(t["file_too_large"].format(max_mb=max_upload_mb))
            else:
                previous_signature = [
                    (item["name"], len(item["bytes"]))
                    for item in st.session_state.get("uploaded_videos", [])
                ]
                next_signature = [(item["name"], len(item["bytes"])) for item in uploaded_videos]
                if previous_signature != next_signature:
                    clear_previous_analysis()
                st.session_state["uploaded_videos"] = uploaded_videos
                current_videos = uploaded_videos
                st.caption(t["upload_summary"].format(count=len(uploaded_videos)))
        elif "uploaded_videos" in st.session_state:
            clear_previous_analysis()
            st.session_state.pop("uploaded_videos", None)
            current_videos = []

    render_support_box(feedback_form_url, support_email)

    provider = server_provider if server_provider in {"auto", "openai", "gemini"} else "auto"
    openai_key = ""
    gemini_key = ""
    model_override = server_model

    if show_api_settings:
        with st.expander(t["api_settings"]):
            st.caption(t["api_settings_help"])
            provider_labels = {
                "auto": t["provider_auto"],
                "openai": t["provider_openai"],
                "gemini": t["provider_gemini"],
            }
            provider = st.selectbox(
                t["provider_label"],
                ["auto", "openai", "gemini"],
                index=["auto", "openai", "gemini"].index(provider),
                format_func=lambda option: provider_labels[option],
            )
            if provider in {"auto", "openai"} and not server_openai_key:
                openai_key = st.text_input(t["openai_key_label"], type="password")
            if provider in {"auto", "gemini"} and not server_gemini_key:
                gemini_key = st.text_input(t["gemini_key_label"], type="password")
            model_override = st.text_input(t["model_label"], value=model_override)

with media_col:
    video_tab, pose_tab = st.tabs([t["video_tab"], t["pose_tab"]])
    with video_tab:
        if current_videos:
            st.video(current_videos[0]["bytes"])
            if len(current_videos) > 1:
                st.caption(t["upload_summary"].format(count=len(current_videos)))
        else:
            st.info(t["waiting"])
    with pose_tab:
        if "analyzed_image_bytes" in st.session_state:
            st.image(st.session_state["analyzed_image_bytes"], use_container_width=True)
        else:
            st.info(t["empty_pose"])

can_analyze = bool(current_videos) and payment_unlocked

if st.button(t["start_label"], type="primary", disabled=not can_analyze, use_container_width=True):
    now = time.monotonic()
    last_analysis_at = st.session_state.get("last_analysis_at", 0)
    seconds_since_last_analysis = now - last_analysis_at
    if seconds_since_last_analysis < analysis_cooldown_seconds:
        wait_seconds = int(analysis_cooldown_seconds - seconds_since_last_analysis) + 1
        st.warning(t["cooldown"].format(seconds=wait_seconds))
        st.stop()

    st.session_state["last_analysis_at"] = now
    clear_previous_analysis()
    work_dir = tempfile.mkdtemp(prefix="basketball-ai-coach-")
    try:
        analysis_ok = False
        analysis_error_key = None
        fallback_analysis = False
        analysis_debug = ""
        metrics = None
        score = None
        stability = None
        analyzed_image_bytes = None

        work_path = Path(work_dir)
        shot_path = work_path / "shot.mp4"
        result_path = work_path / "result.txt"
        stability_path = work_path / "stability.json"
        segments_path = work_path / "segments.json"
        analyzed_image_path = work_path / "release_analyzed.jpg"

        with st.spinner(t["spinner"]):
            source_video_paths = []
            for index, video_item in enumerate(current_videos):
                suffix = Path(video_item["name"]).suffix or ".mp4"
                source_path = work_path / f"source_{index}{suffix}"
                source_path.write_bytes(video_item["bytes"])
                source_video_paths.append(source_path)

            if len(source_video_paths) == 1:
                shot_path.write_bytes(source_video_paths[0].read_bytes())
            else:
                segments = combine_videos(source_video_paths, shot_path)
                segments_path.write_text(json.dumps(segments), encoding="utf-8")

            try:
                analysis_command = [
                    sys.executable,
                    "analyze_release.py",
                    "--input",
                    str(shot_path),
                    "--output-image",
                    str(analyzed_image_path),
                    "--result",
                    str(result_path),
                    "--stability",
                    str(stability_path),
                ]
                if segments_path.exists():
                    analysis_command.extend(["--segments", str(segments_path)])

                analysis = subprocess.run(
                    analysis_command,
                    cwd=BASE_DIR,
                    capture_output=True,
                    text=True,
                    timeout=90,
                )
            except subprocess.TimeoutExpired:
                analysis_error_key = "analysis_timeout"
                analysis = None

            if analysis_error_key is None and analysis.returncode != 0:
                analysis_debug = (analysis.stdout or "") + "\n" + (analysis.stderr or "")
                if "NO_SHOOTING_MOTION" in analysis_debug:
                    analysis_error_key = "not_shot_video"
                else:
                    fallback_analysis = True

            if analysis_error_key is None and not fallback_analysis:
                try:
                    metrics = load_metrics(result_path)
                    stability = load_stability(stability_path)
                except (FileNotFoundError, OSError, ValueError, TypeError):
                    fallback_analysis = True

            if analysis_error_key is None and not fallback_analysis:
                score = calculate_score(metrics)
                analyzed_image_bytes = analyzed_image_path.read_bytes() if analyzed_image_path.exists() else None
                analysis_ok = True
            elif analysis_error_key is None and fallback_analysis:
                analysis_ok = True

        if not analysis_ok:
            if analysis_error_key == "analysis_timeout":
                st.error(t["analysis_timeout"])
            elif analysis_error_key == "not_shot_video":
                show_not_shot_guidance()
            else:
                show_video_quality_guidance()
                show_debug_details(analysis_debug)
            st.session_state["analysis_error_key"] = analysis_error_key
            st.stop()

        st.success(t["done"])

        if fallback_analysis:
            show_limited_analysis_guidance()
            show_debug_details(analysis_debug)
        else:
            score_col, metrics_col = st.columns([0.65, 1.35], gap="large")
            st.session_state["analysis_metrics"] = metrics
            st.session_state["analysis_score"] = score
            st.session_state["analysis_stability"] = stability
            if not timing_is_reliable(metrics):
                st.warning(t["timing_warning"])

            with score_col:
                st.subheader(t["score_title"])
                st.metric(t["score_label"], f"{score}/100")
                st.markdown(f'<div class="score-note">{t["score_caption"]}</div>', unsafe_allow_html=True)

            with metrics_col:
                st.subheader(t["metrics_title"])
                m1, m2, m3 = st.columns(3)
                with m1:
                    metric_card(t["metric_elbow"], f'{metrics["elbow_angle"]:.1f}°', t["metric_elbow_help"])
                    metric_card(t["metric_dip_knee"], f'{metrics["dip_knee_angle"]:.1f}°', t["metric_dip_knee_help"])
                with m2:
                    metric_card(t["metric_height"], f'{metrics["release_height"]:.1f} px', t["metric_height_help"])
                    metric_card(t["metric_release_knee"], f'{metrics["release_knee_angle"]:.1f}°', t["metric_release_knee_help"])
                with m3:
                    metric_card(t["metric_lean"], f'{metrics["body_lean"]:.1f} px', t["metric_lean_help"])
                    metric_card(t["metric_extension"], f'{metrics["knee_extension"]:.1f}°', t["metric_extension_help"])

                metric_card(t["metric_flow"], f'{metrics["flow_frames"]:.0f}', t["metric_flow_help"])

            render_stability(stability)

            if analyzed_image_bytes:
                st.session_state["analyzed_image_bytes"] = analyzed_image_bytes
                st.image(analyzed_image_bytes, caption=t["pose_tab"], use_container_width=True)

        st.subheader(t["coach_title"])
        coach_env = os.environ.copy()
        if server_openai_key:
            coach_env["OPENAI_API_KEY"] = server_openai_key
        elif openai_key:
            coach_env["OPENAI_API_KEY"] = openai_key

        if server_gemini_key:
            coach_env["GEMINI_API_KEY"] = server_gemini_key
        elif gemini_key:
            coach_env["GEMINI_API_KEY"] = gemini_key

        coach_env["AI_COACH_PROVIDER"] = provider

        has_configured_key = (
            bool(openai_key)
            or bool(gemini_key)
            or bool(coach_env.get("OPENAI_API_KEY"))
            or bool(coach_env.get("GEMINI_API_KEY"))
        )

        if not has_configured_key:
            st.warning(t["missing_key"])
            st.stop()

        coach_command = [
            sys.executable,
            "coach_ai_new.py",
            "--mode",
            mode,
            "--player_model",
            player_model,
            "--lang",
            lang_code,
            "--provider",
            provider,
            "--result",
            str(result_path),
            "--stability",
            str(stability_path),
            "--max_output_tokens",
            str(ai_max_output_tokens),
        ]
        if model_override.strip():
            coach_command.extend(["--model", model_override.strip()])
        if fallback_analysis:
            coach_command.append("--fallback")

        try:
            result = subprocess.run(
                coach_command,
                cwd=BASE_DIR,
                env=coach_env,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.stdout:
                report_notes = clean_report_notes(result.stdout)
                st.session_state["coach_feedback"] = report_notes
                st.markdown(report_notes)
                report_markdown = build_report_markdown(metrics, score, stability, report_notes, fallback_analysis)
                st.session_state["report_markdown"] = report_markdown
                try:
                    st.session_state["report_pdf_bytes"] = make_pdf_report(report_markdown, analyzed_image_bytes)
                    st.download_button(
                        t["download_report"],
                        data=st.session_state["report_pdf_bytes"],
                        file_name="basketball-wurf-check-report.pdf",
                        mime="application/pdf",
                    )
                except Exception:
                    st.download_button(
                        t["download_report"],
                        data=report_markdown.encode("utf-8"),
                        file_name="basketball-wurf-check-report.md",
                        mime="text/markdown",
                    )
            else:
                st.info(t["no_feedback"])

            if result.stderr:
                st.error(t["coach_error"])
        except subprocess.TimeoutExpired:
            st.error(t["coach_timeout"])
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
