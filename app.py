import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import streamlit as st


BASE_DIR = Path(__file__).resolve().parent

LANG_OPTIONS = {
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
        "upload_label": "Upload shooting video",
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
    "zh": {
        "page_title": "AI篮球投篮教练",
        "eyebrow": "视频动作分析",
        "title": "AI篮球投篮教练",
        "desc": "上传一段投篮视频，系统会分析出手动作、下肢发力、身体稳定性，并生成可执行的 AI 教练点评。",
        "language": "语言",
        "settings": "本次分析设置",
        "style_label": "对标风格",
        "mode_label": "点评模式",
        "upload_label": "上传投篮视频",
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


def get_secret(name, default=""):
    if os.getenv(name):
        return os.getenv(name, default)

    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


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
        background: #ffffff;
        border: 1px solid #e7e4de;
        border-radius: 8px;
        padding: 0.85rem 0.95rem;
        min-height: 110px;
    }
    div[data-testid="stMetricLabel"] {
        color: #5b6573;
    }
    .hero {
        border-bottom: 1px solid #e7e4de;
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
        color: #485465;
        max-width: 760px;
        margin-top: 0.55rem;
    }
    .score-note {
        color: #5b6573;
        font-size: 0.9rem;
        margin-top: -0.35rem;
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
    video = st.file_uploader(t["upload_label"], type=["mp4", "mov", "m4v"])
    if video:
        uploaded_video_bytes = video.getvalue()
        if st.session_state.get("uploaded_video_bytes") != uploaded_video_bytes:
            clear_previous_analysis()
        st.session_state["uploaded_video_bytes"] = uploaded_video_bytes
        st.session_state["uploaded_video_name"] = video.name

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
        if "uploaded_video_bytes" in st.session_state:
            st.video(st.session_state["uploaded_video_bytes"])
        else:
            st.info(t["waiting"])
    with pose_tab:
        if "analyzed_image_bytes" in st.session_state:
            st.image(st.session_state["analyzed_image_bytes"], use_container_width=True)
        else:
            st.info(t["empty_pose"])

can_analyze = "uploaded_video_bytes" in st.session_state

if st.button(t["start_label"], type="primary", disabled=not can_analyze, use_container_width=True):
    clear_previous_analysis()
    work_dir = tempfile.mkdtemp(prefix="basketball-ai-coach-")
    try:
        analysis_ok = False
        analysis_error_key = None
        fallback_analysis = False
        metrics = None
        score = None
        analyzed_image_bytes = None

        work_path = Path(work_dir)
        shot_path = work_path / "shot.mp4"
        result_path = work_path / "result.txt"
        analyzed_image_path = work_path / "release_analyzed.jpg"
        shot_path.write_bytes(st.session_state["uploaded_video_bytes"])

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
