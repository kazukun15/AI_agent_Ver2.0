import streamlit as st
import requests
import re
import random

# ========================
#    定数／設定
# ========================
# APIキーは .streamlit/secrets.toml に設定し、st.secrets 経由で取得
API_KEY = st.secrets["general"]["api_key"]
MODEL_NAME = "gemini-2.0-flash-001"
# 固定の日本人キャラクター名
NAMES = ["ゆかり", "しんや", "みのる"]

# ========================
#    関数定義
# ========================

def analyze_question(question: str) -> int:
    score = 0
    keywords_emotional = ["困った", "悩み", "苦しい", "辛い"]
    keywords_logical = ["理由", "原因", "仕組み", "方法"]
    for word in keywords_emotional:
        if re.search(word, question):
            score += 1
    for word in keywords_logical:
        if re.search(word, question):
            score -= 1
    return score

def adjust_parameters(question: str) -> dict:
    score = analyze_question(question)
    params = {}
    if score > 0:
        params["ゆかり"] = {"style": "情熱的", "detail": "感情に寄り添う回答"}
        params["しんや"] = {"style": "共感的", "detail": "心情を重視した解説"}
        params["みのる"] = {"style": "柔軟", "detail": "状況に合わせた多面的な視点"}
    else:
        params["ゆかり"] = {"style": "論理的", "detail": "具体的な解説を重視"}
        params["しんや"] = {"style": "分析的", "detail": "データや事実を踏まえた説明"}
        params["みのる"] = {"style": "客観的", "detail": "中立的な視点からの考察"}
    return params

def remove_json_artifacts(text: str) -> str:
    if not isinstance(text, str):
        text = str(text) if text else ""
    pattern = r"'parts': \[\{'text':.*?\}\], 'role': 'model'"
    cleaned = re.sub(pattern, "", text, flags=re.DOTALL)
    return cleaned.strip()

def call_gemini_api(prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers)
    except Exception as e:
        return f"エラー: リクエスト送信時に例外が発生しました -> {str(e)}"
    if response.status_code != 200:
        return f"エラー: ステータスコード {response.status_code} -> {response.text}"
    try:
        rjson = response.json()
        candidates = rjson.get("candidates", [])
        if not candidates:
            return "回答が見つかりませんでした。(candidatesが空)"
        candidate0 = candidates[0]
        content_val = candidate0.get("content", "")
        if isinstance(content_val, dict):
            parts = content_val.get("parts", [])
            content_str = " ".join([p.get("text", "") for p in parts])
        else:
            content_str = str(content_val)
        content_str = content_str.strip()
        if not content_str:
            return "回答が見つかりませんでした。(contentが空)"
        return remove_json_artifacts(content_str)
    except Exception as e:
        return f"エラー: レスポンス解析に失敗しました -> {str(e)}"

def generate_discussion(question: str, persona_params: dict) -> str:
    prompt = f"【ユーザーの質問】\n{question}\n\n"
    for name, params in persona_params.items():
        prompt += f"{name}は【{params['style']}な視点】で、{params['detail']}。\n"
    prompt += (
        "\n上記情報を元に、3人が友達同士のように自然な会話をしてください。\n"
        "出力形式は以下の通りです。\n"
        "ゆかり: 発言内容\n"
        "しんや: 発言内容\n"
        "みのる: 発言内容\n"
        "余計なJSON形式は入れず、自然な日本語の会話のみを出力してください。"
    )
    return call_gemini_api(prompt)

def continue_discussion(additional_input: str, current_discussion: str) -> str:
    prompt = (
        "これまでの会話:\n" + current_discussion + "\n\n" +
        "ユーザーの追加発言: " + additional_input + "\n\n" +
        "上記を踏まえ、3人がさらに自然な会話を続けてください。\n"
        "出力形式は以下:\n"
        "ゆかり: 発言内容\n"
        "しんや: 発言内容\n"
        "みのる: 発言内容\n"
        "余計なJSON形式は入れず、自然な日本語の会話のみを出力してください。"
    )
    return call_gemini_api(prompt)

def generate_summary(discussion: str) -> str:
    prompt = (
        "以下は3人の会話内容です。\n" + discussion + "\n\n" +
        "この会話を踏まえて、質問に対するまとめ回答を生成してください。\n"
        "自然な日本語文で出力し、余計なJSON形式は不要です。"
    )
    return call_gemini_api(prompt)

def display_line_style(text: str):
    lines = text.split("\n")
    color_map = {
        "ゆかり": {"bg": "#FFD1DC", "color": "#333"},  # 薄いピンク
        "しんや": {"bg": "#D1E8FF", "color": "#333"},  # 薄いブルー
        "みのる": {"bg": "#D1FFD1", "color": "#333"}   # 薄いグリーン
    }
    for line in lines:
        line = line.strip()
        if not line:
            continue
        matched = re.match(r"^(.*?):\s*(.*)$", line)
        if matched:
            name = matched.group(1)
            message = matched.group(2)
        else:
            name = ""
            message = line
        styles = color_map.get(name, {"bg": "#F5F5F5", "color": "#333"})
        bg_color = styles["bg"]
        text_color = styles["color"]
        bubble_html = f"""
        <div style="
            background-color: {bg_color};
            border:1px solid #ddd;
            border-radius:10px;
            padding:8px;
            margin:5px 0;
            width: fit-content;
            color: {text_color};
            font-family: Arial, sans-serif;
        ">
            <strong>{name}</strong><br>
            {message}
        </div>
        """
        st.markdown(bubble_html, unsafe_allow_html=True)

# ========================
#    Streamlit アプリ
# ========================
st.title("ぼくのともだち - 自然な会話 (複数ターン)")

# --- 上部：会話表示エリア ---
st.header("会話履歴")
discussion_container = st.empty()

# --- 下部：入力エリア ---
st.header("メッセージ入力")
user_input = st.text_area("新たな発言を入力してください", placeholder="ここに入力", height=100)
col1, col2 = st.columns([1, 3])
with col1:
    if st.button("会話を開始"):
        if user_input.strip():
            persona_params = adjust_parameters(user_input)
            discussion = generate_discussion(user_input, persona_params)
            st.session_state["discussion"] = discussion
            discussion_container.markdown("### 3人の会話\n" + discussion)
        else:
            st.warning("発言を入力してください。")
with col2:
    if st.button("会話を続ける"):
        if user_input.strip() and st.session_state.get("discussion", ""):
            new_discussion = continue_discussion(user_input, st.session_state["discussion"])
            st.session_state["discussion"] += "\n" + new_discussion
            discussion_container.markdown("### 3人の会話\n" + st.session_state["discussion"])
        else:
            st.warning("まずは初回の会話を開始してください。")

# --- まとめ回答生成エリア ---
st.header("まとめ回答")
if st.button("会話をまとめる"):
    if st.session_state.get("discussion", ""):
        summary = generate_summary(st.session_state["discussion"])
        st.session_state["summary"] = summary
        st.markdown("### まとめ回答\n" + "**まとめ:** " + summary)
    else:
        st.warning("まずは会話を開始してください。")
