import argparse
import json
import os
import sys
from pathlib import Path
from urllib import error, request

from google import genai


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_PROVIDER = os.getenv("AI_COACH_PROVIDER", "auto").lower()
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def load_metrics(result_path):
    data = Path(result_path).read_text(encoding="utf-8").strip().split(",")
    if len(data) != 7:
        raise ValueError("result.txt must contain 7 comma-separated values")

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


def calculate_score(metrics):
    score = 100

    if metrics["elbow_angle"] < 150:
        score -= min(20, (150 - metrics["elbow_angle"]) * 0.8)
    elif metrics["elbow_angle"] > 175:
        score -= min(15, (metrics["elbow_angle"] - 175) * 0.8)

    if metrics["release_height"] < 0:
        score -= 20
    elif metrics["release_height"] < 20:
        score -= 10

    if abs(metrics["body_lean"]) > 40:
        score -= 15
    elif abs(metrics["body_lean"]) > 20:
        score -= 8

    if metrics["knee_extension"] < 30:
        score -= 15
    elif metrics["knee_extension"] < 50:
        score -= 8

    if metrics["flow_frames"] > 40:
        score -= 12
    elif metrics["flow_frames"] > 25:
        score -= 6
    elif metrics["flow_frames"] < 5:
        score -= 6

    return max(0, min(100, round(score)))


PLAYER_PROFILES = {
    "zh": {
        "curry": """
对标风格：Stephen Curry
重点参考：
- 出手节奏快
- 动作连贯，不停顿
- 下肢、核心、手臂衔接顺
- 出手不一定最高，但释放快、稳定、柔和
""",
        "durant": """
对标风格：Kevin Durant
重点参考：
- 出手点极高
- 身体延展充分
- 手臂伸展完整
- 投篮不容易被封盖
""",
        "thompson": """
对标风格：Klay Thompson
重点参考：
- 动作极简
- 接球投节奏稳定
- 身体垂直，出手线路干净
- 下肢发力和上肢释放同步
""",
        "general": """
对标风格：通用标准投篮
重点参考：
- 出手稳定
- 身体平衡
- 下肢参与
- 动作可重复
""",
    },
    "en": {
        "curry": """
Reference style: Stephen Curry
Focus:
- Fast release rhythm
- Smooth, continuous motion without a visible pause
- Connected lower body, core, and shooting arm
- Release is not always the highest, but it is quick, stable, and soft
""",
        "durant": """
Reference style: Kevin Durant
Focus:
- Very high release point
- Full body extension
- Complete arm extension
- Shot is difficult to contest
""",
        "thompson": """
Reference style: Klay Thompson
Focus:
- Minimal, repeatable motion
- Stable catch-and-shoot rhythm
- Vertical body line and clean release path
- Lower-body force and upper-body release stay synchronized
""",
        "general": """
Reference style: General shooting mechanics
Focus:
- Stable release
- Body balance
- Lower-body contribution
- Repeatable motion
""",
    },
    "de": {
        "curry": """
Referenzstil: Stephen Curry
Fokus:
- Schneller Release-Rhythmus
- Fließende Bewegung ohne sichtbare Pause
- Gute Verbindung von Beinen, Core und Wurfarm
- Release ist nicht immer maximal hoch, aber schnell, stabil und weich
""",
        "durant": """
Referenzstil: Kevin Durant
Fokus:
- Sehr hoher Release-Punkt
- Vollständige Körperstreckung
- Komplette Armstreckung
- Schwer zu blockender Wurf
""",
        "thompson": """
Referenzstil: Klay Thompson
Fokus:
- Minimale, wiederholbare Bewegung
- Stabiler Catch-and-Shoot Rhythmus
- Vertikale Körperlinie und sauberer Release-Pfad
- Beinimpuls und Oberkörper-Release bleiben synchron
""",
        "general": """
Referenzstil: Allgemeine Wurfmechanik
Fokus:
- Stabiler Release
- Körperbalance
- Beteiligung der Beine
- Wiederholbare Bewegung
""",
    },
}


def build_prompt(metrics, score, mode, player_model, lang):
    profile_text = PLAYER_PROFILES[lang][player_model]

    if lang == "de":
        shared = f"""
Du bist ein professioneller Basketball-Wurfcoach.

{profile_text}

Wurfdaten:
- Ellbogenwinkel beim Release: {metrics["elbow_angle"]} Grad
- Release-Höhe relativ zum Kopf: {metrics["release_height"]}
- Körperneigung: {metrics["body_lean"]}
- Kniewinkel am tiefsten Dip: {metrics["dip_knee_angle"]} Grad
- Kniewinkel beim Release: {metrics["release_knee_angle"]} Grad
- Kniestreckung: {metrics["knee_extension"]} Grad
- Frames vom Load bis zum Release: {metrics["flow_frames"]}
- Gesamt-Form-Score: {score}/100

Scoring-Regel:
Erkläre, dass dieser Score die Qualität der Form, Balance, Timing und Wiederholbarkeit beschreibt. Beschreibe ihn nicht als Trefferquote.

Wichtige Prinzipien:
- Rhythmus und Kontinuität sind Basismerkmale guter Wurfqualität.
- Der Star-Stil ist nur eine Trainingsreferenz, keine starre Bewertungsschablone.
- Bewerte zuerst die grundlegende Wurfmechanik, dann den Bezug zum gewählten Stil.
- Das ist eine Analyse von Stabilität und Wiederholbarkeit, keine Aussage darüber, ob der einzelne Wurf getroffen wurde.
- Lehne den ganzen Wurf nicht wegen eines einzelnen Messwerts ab.
- Fordere nicht, den Star mechanisch zu kopieren.
"""
        if mode == "quick":
            return shared + """
Gib kurze Abschnitte aus:

[Referenzstil]
Ein Satz zum gewählten Stil.

[Score]
Ein Satz, was der Form-Score bedeutet.

[Fazit]
Ein Satz zur Gesamtbewegung.

[Stärken]
Maximal 2 Punkte.

[Optimierung]
Maximal 2 Punkte.

[Wichtigster Fokus]
Maximal 2 wichtigste Stärken oder Probleme.

[Nächster Schritt]
Immer 1 konkretes Detail nennen, das verbessert werden kann.

[Übungen]
Maximal 2 Trainingsvorschläge.

Anforderungen:
- Kling wie ein echter Coach
- Unter 10 Zeilen bleiben
- Nicht nur "gut" sagen
- Auf Deutsch ausgeben
"""

        return shared + """
Analysiere:
1. Ob der Ellbogenwinkel sinnvoll ist
2. Ob die Release-Höhe niedrig, hoch oder passend ist
3. Ob die Beine genug Power beitragen
4. Rhythmus und Kontinuität der Wurfbewegung
5. Gesamtqualität der Form
6. Was der Score bedeutet
7. Welche Teile zum gewählten Referenzstil passen und wie der Spieler näher daran kommt
8. Zwei gezielte Trainingsvorschläge

Anforderungen:
- Professionell und konstruktiv
- Probleme nicht übertreiben
- Wie ein Coach klingen
- Auf Deutsch ausgeben
"""

    if lang == "en":
        shared = f"""
You are a professional basketball shooting coach.

{profile_text}

Shot data:
- Elbow angle at release: {metrics["elbow_angle"]} degrees
- Release height relative to head: {metrics["release_height"]}
- Body lean: {metrics["body_lean"]}
- Knee angle at lowest dip: {metrics["dip_knee_angle"]} degrees
- Knee angle at release: {metrics["release_knee_angle"]} degrees
- Knee extension: {metrics["knee_extension"]} degrees
- Frames from power load to release: {metrics["flow_frames"]}
- Overall form score: {score}/100

Scoring rule:
Explain that this score reflects form quality, balance, timing, and repeatability. Do not describe it as shot make percentage.

Important principles:
- Rhythm and continuity are core shooting-quality indicators, not traits of only one star player.
- The star template is a training reference, not a rigid grading rule.
- Evaluate basic shooting mechanics first, then explain how the player could move closer to the selected style.
- This is analysis of stability and repeatability, not a prediction that the shot went in or missed.
- Do not reject the whole shot because of one imperfect metric.
- Do not tell the player to mechanically copy the star.
"""
        if mode == "quick":
            return shared + """
Output with these short sections:

[Reference style]
One sentence naming the selected style.

[Score]
One sentence explaining the form score.

[Conclusion]
One sentence evaluating the overall movement.

[Similarities]
At most 2 points.

[Gaps / optimizations]
At most 2 points.

[Key points]
At most 2 most important strengths or problems.

[Next improvement]
Always give 1 detail to improve, even if the motion is good.

[Drills]
At most 2 training suggestions.

Requirements:
- Sound like a real coach
- Keep it under 10 lines
- Do not only say "good"
- Output in English
"""

        return shared + """
Analyze:
1. Whether the elbow angle is reasonable
2. Whether the release height is low, high, or appropriate
3. Whether the legs contribute enough power
4. Overall shooting rhythm and continuity
5. Overall form quality
6. What the score means
7. Which parts match the selected reference style and how to move closer to it
8. Two targeted training suggestions

Requirements:
- Professional and constructive
- Do not exaggerate problems
- Sound like a coach
- Output in English
"""

    shared = f"""
你是一名专业篮球投篮教练。

{profile_text}

投篮数据：
- 出手瞬间手肘角度：{metrics["elbow_angle"]}度
- 出手高度（相对头部）：{metrics["release_height"]}
- 身体前倾程度：{metrics["body_lean"]}
- 下蹲最低点膝盖角度：{metrics["dip_knee_angle"]}度
- 出手时膝盖角度：{metrics["release_knee_angle"]}度
- 膝盖伸展幅度：{metrics["knee_extension"]}度
- 发力到出手帧数：{metrics["flow_frames"]}
- 综合动作评分：{score}/100

【评分】
说明这个分数代表动作质量、平衡、节奏和可重复性，不要说成绝对命中率。

重要原则：
- 连贯性是基础投篮质量指标，不属于任何单一球星风格。
- 球星模板只用于训练方向参考，不用于机械判断动作好坏。
- 先基于基础投篮力学评价动作，再说明如果对标该球星风格，可以额外优化什么。
- 这是动作稳定性和可重复性分析，不是判断这个球一定进或不进。
- 不要因为某一个指标不理想就直接否定整个投篮动作。
- 不要机械要求球员完全模仿球星。
"""
    if mode == "quick":
        return shared + """
请输出：

【对标风格】
一句话说明当前选择的球星风格。

【评分】
一句话解释这个分数代表的动作质量。

【结论】
一句话评价整体水平。

【接近点】
最多2点，说明哪些地方接近该球星风格。

【差距/优化点】
最多2点，说明如果想往这个风格靠近，应该优化什么。

【关键点】
最多2点，说明最重要优点或问题。

【优化点】
即使动作很好，也必须给出1个可以进一步提升的细节。

【建议】
最多2条训练建议。

要求：
- 像真实教练
- 不超过10行
- 不要只说“很好”
- 必须指出一个可提升点
- 用中文输出
"""

    return shared + """
请分析：
1. 手肘角度是否合理
2. 出手高度是否偏低或偏高
3. 腿部动作是否足够
4. 整体投篮动作连贯性
5. 综合评价投篮动作
6. 一句话解释这个分数代表的动作质量
7. 哪些地方接近该球星风格，以及如果要接近这个球星该如何改进
8. 给出2条针对性训练建议

要求：
- 专业
- 不要夸大问题
- 像教练
- 用中文输出
"""


def build_fallback_prompt(mode, player_model, lang):
    profile_text = PLAYER_PROFILES[lang][player_model]

    if lang == "de":
        detail = "kurzes" if mode == "quick" else "etwas detaillierteres"
        return f"""
Du bist ein professioneller Basketball-Wurfcoach.

{profile_text}

Das hochgeladene Wurfvideo konnte nicht zuverlässig mit Körperpunkten vermessen werden.
Gib trotzdem ein {detail}, hilfreiches Coach-Feedback für einen grundlegenden Wurfclip.

Wichtig:
- Behaupte keine exakten Winkel, Release-Höhe, Timing-Werte oder Kniestreckung.
- Erkläre, dass ein klareres Ganzkörpervideo von der Seite genauere biomechanische Werte ermöglichen würde.
- Gib praktisches Feedback zu Balance, Set Point, Release-Pfad, Follow-through, Beinrhythmus und Wiederholbarkeit.
- Konstruktiver Coach-Ton.
- Auf Deutsch ausgeben.
"""

    if lang == "en":
        detail = "brief" if mode == "quick" else "more detailed"
        return f"""
You are a professional basketball shooting coach.

{profile_text}

The uploaded shooting video could not be measured reliably with pose landmarks.
Still provide a {detail} coach response that is useful for a basic shooting clip.

Important:
- Do not claim exact body angles, release height, timing, or knee extension.
- Explain that a clearer side-view full-body video would allow more precise biomechanical metrics.
- Give practical feedback a player can use: balance, set point, release path, follow-through, lower-body rhythm, and repeatability.
- Keep the tone constructive and coach-like.
- Output in English.
"""

    detail = "简短" if mode == "quick" else "相对详细"
    return f"""
你是一名专业篮球投篮教练。

{profile_text}

这段投篮视频暂时无法稳定提取人体关键点指标。
请仍然给出一个{detail}、有用的基础教练点评。

重要要求：
- 不要声称已经测得具体角度、出手高度、节奏帧数或膝盖伸展幅度。
- 说明如果视频是更清楚的侧面全身视角，就可以提供更精确的生物力学指标。
- 给出球员马上能执行的建议：平衡、出手点、出手线路、随球动作、下肢节奏、动作可重复性。
- 语气像真实教练，建设性，不要责怪用户。
- 用中文输出。
"""


def pick_provider(provider):
    if provider != "auto":
        return provider

    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("GEMINI_API_KEY"):
        return "gemini"

    raise RuntimeError(
        "No AI provider is configured. Set OPENAI_API_KEY or GEMINI_API_KEY, "
        "or set AI_COACH_PROVIDER explicitly."
    )


def generate_with_gemini(prompt, model):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )
    return response.text or ""


def extract_openai_text(payload):
    if payload.get("output_text"):
        return payload["output_text"]

    chunks = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                chunks.append(content["text"])
    return "\n".join(chunks)


def generate_with_openai(prompt, model):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    body = json.dumps(
        {
            "model": model,
            "input": prompt,
        }
    ).encode("utf-8")

    req = request.Request(
        "https://api.openai.com/v1/responses",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API error {exc.code}: {detail}") from exc

    return extract_openai_text(payload)


def generate_feedback(prompt, provider, model):
    selected_provider = pick_provider(provider)

    if selected_provider == "gemini":
        selected_model = model or DEFAULT_GEMINI_MODEL
        return generate_with_gemini(prompt, selected_model)

    if selected_provider == "openai":
        selected_model = model or DEFAULT_OPENAI_MODEL
        return generate_with_openai(prompt, selected_model)

    raise RuntimeError("AI_COACH_PROVIDER must be auto, gemini, or openai.")


parser = argparse.ArgumentParser()
parser.add_argument("--mode", default="quick", choices=["quick", "detailed"])
parser.add_argument("--player_model", default="general", choices=["general", "curry", "durant", "thompson"])
parser.add_argument("--lang", default="zh", choices=["zh", "en", "de"])
parser.add_argument("--provider", default=DEFAULT_PROVIDER, choices=["auto", "gemini", "openai"])
parser.add_argument("--model", default="")
parser.add_argument("--result", default=str(BASE_DIR / "result.txt"))
parser.add_argument("--fallback", action="store_true")
args = parser.parse_args()

if args.fallback:
    prompt = build_fallback_prompt(args.mode, args.player_model, args.lang)
else:
    metrics = load_metrics(args.result)
    score = calculate_score(metrics)
    prompt = build_prompt(metrics, score, args.mode, args.player_model, args.lang)

status_text = {
    "en": "Generating AI coach feedback...",
    "de": "Erstelle AI Coach-Feedback...",
    "zh": "正在生成 AI 教练点评...",
}[args.lang]
heading = {
    "en": "===== AI Coach Feedback =====",
    "de": "===== AI Coach-Feedback =====",
    "zh": "===== AI教练点评 =====",
}[args.lang]

print(status_text, flush=True)

try:
    feedback = generate_feedback(prompt, args.provider, args.model)
except RuntimeError as exc:
    print(str(exc), file=sys.stderr)
    sys.exit(1)

print(f"\n{heading}\n")
print(feedback)
