import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
TALLY_INTEREST_URL = "https://tally.so/r/oblEQO"

LANG_OPTIONS = {
    "Deutsch": "de",
    "English": "en",
    "中文": "zh",
}

TEXT = {
    "en": {
        "page_title": "AI Basketball Shot Coach",
        "eyebrow": "Video form analysis",
        "title": "AI Basketball Shot Coach",
        "desc": "Upload a shooting video to analyze release mechanics, lower-body power, balance, and receive practical AI coach feedback.",
        "language": "Language",
        "settings": "Session setup",
        "style_label": "Reference style",
        "mode_label": "Feedback mode",
        "source_label": "Video source",
        "source_record": "Record with phone camera",
        "source_upload": "Upload existing video",
        "upload_label": "Upload shooting video",
        "record_upload_label": "Record or choose a shooting video",
        "record_hint": "On a phone, tap Upload and choose the camera/video option. On desktop, upload a saved video file.",
        "record_checklist_title": "Before recording, check this:",
        "record_checklist": """
- Film 3-8 seconds, one complete shot only
- Use landscape or portrait, but keep the full body visible
- Stand 2-4 meters from the camera
- Best angle: side view or about 45 degrees
- Keep feet, knees, shooting hand, and follow-through in frame
- Good light, steady phone, no slow-motion or edits
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
        "missing_key": "Add an API key in AI API settings before generating coach feedback.",
        "file_too_large": "This video is too large. Please upload a file up to {max_mb} MB.",
        "cooldown": "Please wait {seconds} more seconds before starting another analysis.",
        "start_label": "Start analysis",
        "quick_label": "Quick feedback",
        "detailed_label": "Detailed report",
        "video_tab": "Shot video",
        "pose_tab": "Release pose",
        "empty_pose": "Run analysis to generate the annotated release pose.",
        "waiting": "Upload a video to begin.",
        "spinner": "Analyzing mechanics and preparing coach feedback...",
        "done": "Analysis complete.",
        "analysis_error": "Motion analysis failed.",
        "result_missing": "Analysis did not produce a valid result file.",
        "result_invalid": "The result file is incomplete or unreadable.",
        "analysis_timeout": "Analysis took too long and was stopped.",
        "quality_title": "This video could not be analyzed reliably.",
        "quality_guidance": """
Please upload a short, clear shooting clip:
- 3-8 seconds, no edits, cuts, or slow-motion effects
- Full body visible from feet to shooting hand throughout the shot
- Side view or 45-degree angle, with only one main shooter in frame
- Good lighting, steady camera, and at least 720p resolution
- Include the full motion: dip/load, jump or extension, release, and follow-through
""",
        "limited_title": "Limited video analysis",
        "limited_guidance": "The app could not extract reliable body landmarks from this clip, so exact angle metrics are unavailable. It will still provide basic coach feedback. A clearer full-body side-view video can unlock more detailed biomechanics.",
        "debug_details": "Analysis diagnostics",
        "timing_warning": "The pose was detected, but the loading-to-release timing may be unreliable for this clip. The coach feedback will focus more on visible posture metrics.",
        "coach_error": "AI coach feedback returned an error:",
        "coach_timeout": "AI coach feedback timed out. Please retry later or use quick feedback.",
        "score_title": "Form score",
        "score_label": "Shot mechanics",
        "score_caption": "A form-quality score for balance, timing, and repeatability. It is not a make-percentage prediction.",
        "metrics_title": "Key biomechanics",
        "coach_title": "AI coach feedback",
        "no_feedback": "No coach feedback was returned.",
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
        "page_title": "KI Basketball Wurfanalyse",
        "eyebrow": "Video-Wurfanalyse",
        "title": "KI Basketball Wurfanalyse",
        "desc": "Lade ein Wurfvideo hoch und erhalte eine technische Analyse zu Release, Beinarbeit, Balance und konkreten Coach-Hinweisen.",
        "language": "Sprache",
        "settings": "Analyse starten",
        "style_label": "Referenzstil",
        "mode_label": "Berichtsart",
        "source_label": "Videoquelle",
        "source_record": "Mit dem Handy aufnehmen",
        "source_upload": "Vorhandenes Video hochladen",
        "upload_label": "Wurfvideo hochladen",
        "record_upload_label": "Wurfvideo aufnehmen oder auswählen",
        "record_hint": "Am Handy auf Upload tippen und Kamera/Video auswählen. Am Computer kannst du eine gespeicherte Videodatei hochladen.",
        "record_checklist_title": "Vor dem Aufnehmen kurz prüfen:",
        "record_checklist": """
- 3-8 Sekunden filmen, nur einen vollständigen Wurf
- Querformat oder Hochformat ist okay, aber der ganze Körper muss sichtbar bleiben
- Kamera etwa 2-4 Meter entfernt platzieren
- Beste Perspektive: Seitenansicht oder etwa 45 Grad
- Füße, Knie, Wurfhand und Follow-through bleiben im Bild
- Gute Beleuchtung, ruhiges Handy, keine Zeitlupe oder Schnitte
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
        "missing_key": "Bitte zuerst einen API key konfigurieren, um Coach-Feedback zu erzeugen.",
        "file_too_large": "Dieses Video ist zu groß. Bitte lade maximal {max_mb} MB hoch.",
        "cooldown": "Bitte warte noch {seconds} Sekunden, bevor du die nächste Analyse startest.",
        "start_label": "Analyse starten",
        "quick_label": "Kurzfeedback",
        "detailed_label": "Detailbericht",
        "video_tab": "Wurfvideo",
        "pose_tab": "Release-Pose",
        "empty_pose": "Starte die Analyse, um die markierte Release-Pose zu erzeugen.",
        "waiting": "Lade ein Video hoch, um zu beginnen.",
        "spinner": "Analysiere Wurfmechanik und erstelle Coach-Feedback...",
        "done": "Analyse abgeschlossen.",
        "analysis_error": "Bewegungsanalyse fehlgeschlagen.",
        "result_missing": "Die Analyse hat keine gültige Ergebnisdatei erzeugt.",
        "result_invalid": "Die Ergebnisdatei ist unvollständig oder nicht lesbar.",
        "analysis_timeout": "Die Analyse hat zu lange gedauert und wurde gestoppt.",
        "quality_title": "Dieses Video konnte nicht zuverlässig analysiert werden.",
        "quality_guidance": """
Bitte lade einen kurzen, klaren Wurfclip hoch:
- 3-8 Sekunden, ohne Schnitte, Übergänge oder Zeitlupe
- Der ganze Körper ist vom Fuß bis zur Wurfhand sichtbar
- Seitenansicht oder 45-Grad-Winkel, möglichst nur eine Person im Bild
- Gute Beleuchtung, ruhige Kamera, idealerweise mindestens 720p
- Vollständige Bewegung: Dip/Load, Streckung, Release und Follow-through
""",
        "limited_title": "Eingeschränkte Videoanalyse",
        "limited_guidance": "Das System konnte aus diesem Clip keine stabilen Körperpunkte extrahieren. Exakte Winkelwerte werden deshalb nicht angezeigt, aber du erhältst trotzdem grundlegendes Coach-Feedback. Ein klareres Ganzkörpervideo von der Seite ermöglicht detailliertere Biomechanik.",
        "debug_details": "Analyse-Diagnose",
        "timing_warning": "Die Pose wurde erkannt, aber der Timing-Wert vom Load bis zum Release ist bei diesem Clip möglicherweise unzuverlässig.",
        "coach_error": "AI Coach-Feedback hat einen Fehler zurückgegeben:",
        "coach_timeout": "AI Coach-Feedback hat zu lange gedauert. Bitte später erneut versuchen oder Kurzfeedback nutzen.",
        "score_title": "Form-Score",
        "score_label": "Wurfmechanik",
        "score_caption": "Ein Qualitätswert für Balance, Timing und Wiederholbarkeit. Er ist keine Trefferwahrscheinlichkeit.",
        "metrics_title": "Wichtige Biomechanik",
        "coach_title": "AI Coach-Feedback",
        "no_feedback": "Es wurde kein Coach-Feedback zurückgegeben.",
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
        "page_title": "AI篮球投篮教练",
        "eyebrow": "视频动作分析",
        "title": "AI篮球投篮教练",
        "desc": "上传一段投篮视频，系统会分析出手动作、下肢发力、身体稳定性，并生成可执行的 AI 教练点评。",
        "language": "语言",
        "settings": "本次分析设置",
        "style_label": "对标风格",
        "mode_label": "点评模式",
        "source_label": "视频来源",
        "source_record": "用手机现场拍摄",
        "source_upload": "上传已有视频",
        "upload_label": "上传投篮视频",
        "record_upload_label": "拍摄或选择投篮视频",
        "record_hint": "在手机上点击上传，选择相机/视频拍摄；在电脑上可以上传已保存的视频文件。",
        "record_checklist_title": "拍摄前请确认：",
        "record_checklist": """
- 拍 3-8 秒，只包含一次完整投篮
- 横屏或竖屏都可以，但全身必须始终可见
- 手机距离人大约 2-4 米
- 最佳角度：侧面或约 45 度
- 脚、膝盖、投篮手和随球动作都在画面里
- 光线充足、手机稳定，不要慢动作或剪辑
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
        "missing_key": "请先在 AI API 设置中填写 API key，再生成教练点评。",
        "file_too_large": "这个视频文件太大。请上传不超过 {max_mb} MB 的视频。",
        "cooldown": "请再等待 {seconds} 秒后开始下一次分析。",
        "start_label": "开始分析",
        "quick_label": "快速点评",
        "detailed_label": "深度报告",
        "video_tab": "投篮视频",
        "pose_tab": "出手姿态",
        "empty_pose": "完成分析后会生成带关键点的出手姿态图。",
        "waiting": "先上传一段视频开始分析。",
        "spinner": "正在分析投篮动作并生成教练反馈...",
        "done": "分析完成！",
        "analysis_error": "动作分析失败。",
        "result_missing": "分析没有生成有效的结果文件。",
        "result_invalid": "结果文件不完整或无法读取。",
        "analysis_timeout": "分析时间过长，已停止处理。",
        "quality_title": "这段视频无法被稳定分析。",
        "quality_guidance": """
请上传一段更适合动作识别的投篮视频：
- 时长 3-8 秒，不要剪辑、转场或慢动作特效
- 从脚到投篮手全身始终清楚可见
- 侧面或 45 度角拍摄，画面里尽量只有一个主要投篮人
- 光线充足、镜头稳定，建议至少 720p
- 包含完整动作：下蹲蓄力、起跳或伸展、出手、随球动作
""",
        "limited_title": "基础视频分析",
        "limited_guidance": "系统暂时无法从这段视频中稳定提取人体关键点，所以不会显示精确角度指标。但仍会给出基础教练点评；如果上传更清楚的侧面全身视频，可以获得更详细的生物力学分析。",
        "debug_details": "分析诊断信息",
        "timing_warning": "系统已识别到人体姿态，但这段视频的“蓄力到出手节奏”指标可能不稳定。本次点评会更多参考可见姿态指标。",
        "coach_error": "AI 教练点评生成失败：",
        "coach_timeout": "AI 教练点评响应超时。可以稍后重试，或改用快速点评。",
        "score_title": "综合评分",
        "score_label": "投篮动作",
        "score_caption": "这是关于平衡、节奏和可重复性的动作质量评分，不代表这次投篮的命中率。",
        "metrics_title": "关键生物力学指标",
        "coach_title": "AI教练点评",
        "no_feedback": "没有返回教练点评。",
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
        "headline": "Wurfanalyse ab 1,99 Euro testen",
        "subhead": "Kein App-Download, kein Abo. Lade ein kurzes Wurfvideo hoch und erhalte einen verständlichen Technikbericht mit Score, Messwerten und konkreten Übungen.",
        "cta": "Video hochladen",
        "price": "Geplanter Testpreis: 1,99 Euro pro Basisbericht",
        "proof": "Für Spieler, Eltern und Coaches, die schnell wissen wollen: Was macht meinen Wurf unkonstant?",
        "cards": [
            ("Was du bekommst", "Form-Score, Release-Pose, Ellbogenwinkel, Kniewinkel, Körperneigung und Coach-Feedback."),
            ("Wofür es gedacht ist", "Ein schneller Check für Sprungwurf, Freiwurf oder Catch-and-Shoot Technik."),
            ("Was es nicht ist", "Keine medizinische Beratung und keine Garantie, ob der einzelne Wurf getroffen wurde."),
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
        "interest_title": "Würdest du so einen Bericht testen?",
        "interest_text": "Hilf mit, den ersten bezahlten Test zu formen. Die Registrierung ist noch keine Bestellung und dauert weniger als eine Minute.",
        "interest_submit": "Interesse vormerken",
        "interest_hint": "Öffnet ein kurzes Tally-Formular in einem neuen Tab.",
    },
    "en": {
        "headline": "Test shot analysis from 1.99 Euro",
        "subhead": "No app download and no subscription. Upload a short shooting clip and get a clear technique report with a score, mechanics, and practical drills.",
        "cta": "Upload video",
        "price": "Planned test price: 1.99 Euro per basic report",
        "proof": "For players, parents, and coaches who want to know what makes a shot inconsistent.",
        "cards": [
            ("What you get", "Form score, release pose, elbow angle, knee angles, body lean, and coach feedback."),
            ("Best use case", "A fast check for jump shots, free throws, or catch-and-shoot mechanics."),
            ("What it is not", "Not medical advice and not a guarantee that one shot went in or missed."),
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
        "interest_title": "Would you test this report?",
        "interest_text": "Help shape the first paid test. This is not an order yet and takes less than a minute.",
        "interest_submit": "Register interest",
        "interest_hint": "Opens a short Tally form in a new tab.",
    },
    "zh": {
        "headline": "先测试 1.99 欧元投篮报告",
        "subhead": "不用下载 App，也不用订阅。上传一段短投篮视频，获得包含评分、动作指标和训练建议的技术报告。",
        "cta": "上传视频",
        "price": "计划测试价：基础报告每份 1.99 欧元",
        "proof": "适合想快速知道“为什么投篮不稳定”的球员、家长和教练。",
        "cards": [
            ("你会得到什么", "动作评分、出手姿态图、手肘角度、膝盖角度、身体前倾和教练反馈。"),
            ("适合什么场景", "快速检查跳投、罚球或接球投的基础动作。"),
            ("它不是什么", "不是医疗建议，也不判断单次投篮一定进或不进。"),
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
        "interest_title": "你会愿意测试这份报告吗？",
        "interest_text": "帮我们确定第一版付费测试的方向。这还不是正式订单，填写不到一分钟。",
        "interest_submit": "登记兴趣",
        "interest_hint": "会在新标签页打开一个简短的 Tally 表单。",
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


def timing_is_reliable(metrics):
    return metrics["flow_frames"] > 0


def show_video_quality_guidance():
    st.error(t["quality_title"])
    st.info(t["quality_guidance"])


def show_limited_analysis_guidance():
    st.warning(t["limited_title"])
    st.info(t["limited_guidance"])


def show_debug_details(details):
    if get_secret("SHOW_DEBUG_DETAILS", "false").lower() == "true" and details:
        with st.expander(t["debug_details"]):
            st.text(details[-2000:])


def clear_previous_analysis():
    for key in [
        "analyzed_image_bytes",
        "analysis_metrics",
        "analysis_score",
        "coach_feedback",
        "analysis_error_key",
    ]:
        st.session_state.pop(key, None)


def metric_card(label, value, help_text):
    st.metric(label, value)
    st.caption(help_text)


def render_landing(lang_code):
    landing = LANDING[lang_code]
    st.markdown(
        f"""
        <section class="market-hero">
            <div class="market-copy">
                <div class="eyebrow">{t["eyebrow"]}</div>
                <h1>{landing["headline"]}</h1>
                <p>{landing["subhead"]}</p>
                <div class="market-price">{landing["price"]}</div>
                <div class="market-proof">{landing["proof"]}</div>
            </div>
        </section>
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

    st.markdown(f"#### {landing['questions_title']}")
    q_cols = st.columns([1, 1])
    for index, question in enumerate(landing["questions"]):
        with q_cols[index % 2]:
            st.markdown(f"- {question}")

    st.markdown(f"#### {landing['interest_title']}")
    st.caption(landing["interest_text"])
    st.link_button(landing["interest_submit"], TALLY_INTEREST_URL, type="primary")
    st.caption(landing["interest_hint"])

    st.divider()


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
        padding: 1.2rem;
        margin-bottom: 1rem;
        background: rgba(127, 127, 127, 0.08);
    }
    .market-copy h1 {
        font-size: 2.35rem;
        line-height: 1.08;
        margin: 0;
    }
    .market-copy p {
        max-width: 820px;
        opacity: 0.82;
        margin: 0.7rem 0 0;
    }
    .market-price {
        display: inline-block;
        margin-top: 0.9rem;
        padding: 0.45rem 0.7rem;
        border: 1px solid rgba(248, 113, 113, 0.55);
        border-radius: 6px;
        color: #ff4b4b;
        font-weight: 800;
    }
    .market-proof {
        margin-top: 0.65rem;
        opacity: 0.74;
        font-size: 0.95rem;
    }
    .market-card {
        border: 1px solid rgba(127, 127, 127, 0.24);
        border-radius: 8px;
        padding: 0.95rem;
        min-height: 145px;
        background: rgba(127, 127, 127, 0.07);
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
max_upload_mb = get_int_secret("MAX_UPLOAD_MB", 80, 1, 200)
analysis_cooldown_seconds = get_int_secret("ANALYSIS_COOLDOWN_SECONDS", 20, 0, 300)
ai_max_output_tokens = get_int_secret("AI_COACH_MAX_OUTPUT_TOKENS", 650, 128, 1000)

render_landing(lang_code)

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
current_video_bytes = st.session_state.get("uploaded_video_bytes")

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
    source = st.radio(
        t["source_label"],
        ["record", "upload"],
        format_func=lambda option: t["source_record"] if option == "record" else t["source_upload"],
        horizontal=True,
    )
    if source == "record":
        st.info(f"**{t['record_checklist_title']}**\n{t['record_checklist']}")
        st.caption(t["record_hint"])

    upload_label = t["record_upload_label"] if source == "record" else t["upload_label"]
    video = st.file_uploader(upload_label, type=["mp4", "mov", "m4v", "mpeg4"])
    if video is not None:
        uploaded_video_bytes = video.getvalue()
        max_upload_bytes = max_upload_mb * 1024 * 1024
        if len(uploaded_video_bytes) > max_upload_bytes:
            clear_previous_analysis()
            st.session_state.pop("uploaded_video_bytes", None)
            st.session_state.pop("uploaded_video_name", None)
            current_video_bytes = None
            st.error(t["file_too_large"].format(max_mb=max_upload_mb))
        else:
            if st.session_state.get("uploaded_video_bytes") != uploaded_video_bytes:
                clear_previous_analysis()
            st.session_state["uploaded_video_bytes"] = uploaded_video_bytes
            st.session_state["uploaded_video_name"] = video.name
            current_video_bytes = uploaded_video_bytes

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
        if current_video_bytes:
            st.video(current_video_bytes)
        else:
            st.info(t["waiting"])
    with pose_tab:
        if "analyzed_image_bytes" in st.session_state:
            st.image(st.session_state["analyzed_image_bytes"], use_container_width=True)
        else:
            st.info(t["empty_pose"])

can_analyze = current_video_bytes is not None

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
        analyzed_image_bytes = None

        work_path = Path(work_dir)
        shot_path = work_path / "shot.mp4"
        result_path = work_path / "result.txt"
        analyzed_image_path = work_path / "release_analyzed.jpg"
        shot_path.write_bytes(current_video_bytes)

        with st.spinner(t["spinner"]):
            try:
                analysis = subprocess.run(
                    [
                        sys.executable,
                        "analyze_release.py",
                        "--input",
                        str(shot_path),
                        "--output-image",
                        str(analyzed_image_path),
                        "--result",
                        str(result_path),
                    ],
                    cwd=BASE_DIR,
                    capture_output=True,
                    text=True,
                    timeout=90,
                )
            except subprocess.TimeoutExpired:
                analysis_error_key = "analysis_timeout"
                analysis = None

            if analysis_error_key is None and analysis.returncode != 0:
                fallback_analysis = True
                analysis_debug = (analysis.stdout or "") + "\n" + (analysis.stderr or "")

            if analysis_error_key is None and not fallback_analysis:
                try:
                    metrics = load_metrics(result_path)
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
            show_video_quality_guidance()
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
                st.session_state["coach_feedback"] = result.stdout
                st.markdown(result.stdout)
            else:
                st.info(t["no_feedback"])

            if result.stderr:
                st.error(t["coach_error"])
        except subprocess.TimeoutExpired:
            st.error(t["coach_timeout"])
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
