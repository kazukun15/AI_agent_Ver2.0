import streamlit as st
import requests
import re
import random

# ------------------------
# ページ設定
# ------------------------
st.set_page_config(page_title="ぼくのともだち", layout="wide")

# タイトルの表示
st.title("ぼくのともだち V2.2.1")

# ------------------------
# ユーザーの名前入力（画面上部に表示）
# ------------------------
user_name = st.text_input("あなたの名前を入力してください", value="ユーザー", key="user_name")

# ------------------------
# 定数／設定
# ------------------------
# APIキーは .streamlit/secrets.toml に記述してください
API_KEY = st.secrets["general"]["api_key"]
MODEL_NAME = "gemini-2.0-flash-001"  # 必要に応じて変更
NAMES = ["ゆかり", "しんや", "みのる"]

# ------------------------
# 関数定義
# ------------------------

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
    # ゆかりさんは常に明るくはっちゃけた性格に固定
    params["ゆかり"] = {"style": "明るくはっちゃけた", "detail": "楽しい雰囲気で元気な回答"}
    if score > 0:
        params["しんや"] = {"style": "共感的", "detail": "心情を重視した解説"}
        params["みのる"] = {"style": "柔軟", "detail": "状況に合わせた多面的な視点"}
    else:
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
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
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
    current_user = st.session_state.get("user_name", "ユーザー")
    prompt = f"【{current_user}さんの質問】\n{question}\n\n"
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
        "出力形式は以下の通りです。\n"
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
    """
    各発言をキャラクターごとの背景色と文字色で吹き出し形式に表示する。
    ※ここで、発言の順序を逆転（新しいものが上に来る）して表示します。
    """
    lines = text.split("\n")
    # 空行を除外してリスト化し、逆順にする（最新の発言が先頭に）
    lines = [line.strip() for line in lines if line.strip()]
    lines = list(reversed(lines))
    
    color_map = {
        "ゆかり": {"bg": "#FFD1DC", "color": "#000"},
        "しんや": {"bg": "#D1E8FF", "color": "#000"},
        "みのる": {"bg": "#D1FFD1", "color": "#000"}
    }
    for line in lines:
        matched = re.match(r"^(ゆかり|しんや|みのる):\s*(.*)$", line)
        if matched:
            name = matched.group(1)
            message = matched.group(2)
        else:
            name = ""
            message = line
        styles = color_map.get(name, {"bg": "#F5F5F5", "color": "#000"})
        bubble_html = f"""
        <div style="
            background-color: {styles['bg']};
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 8px;
            margin: 5px 0;
            color: {styles['color']};
            font-family: Arial, sans-serif;
        ">
            <strong>{name}</strong><br>
            {message}
        </div>
        """
        st.markdown(bubble_html, unsafe_allow_html=True)

# ------------------------
# セッションステートの初期化
# ------------------------
if "discussion" not in st.session_state:
    st.session_state["discussion"] = ""

# ------------------------
# 会話まとめボタン（会話がある場合のみ）
# ------------------------
if st.button("会話をまとめる"):
    if st.session_state["discussion"]:
        summary = generate_summary(st.session_state["discussion"])
        st.session_state["summary"] = summary
        st.markdown("### まとめ回答\n" + "**まとめ:** " + summary)
    else:
        st.warning("まずは会話を開始してください。")

# ------------------------
# 固定フッター（入力エリア）の配置
# ------------------------
with st.container():
    st.markdown('<div class="fixed-footer">', unsafe_allow_html=True)
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_area("新たな発言を入力してください", placeholder="ここに入力", height=100, key="user_input")
        # 2つのボタンを横並びで配置
        col1, col2 = st.columns(2)
        with col1:
            send_button = st.form_submit_button("送信")
        with col2:
            continue_button = st.form_submit_button("続きを話す")
    st.markdown('</div>', unsafe_allow_html=True)

    # 送信ボタンが押された場合の処理
    if send_button:
        if user_input.strip():
            if not st.session_state["discussion"]:
                persona_params = adjust_parameters(user_input)
                discussion = generate_discussion(user_input, persona_params)
                st.session_state["discussion"] = discussion
            else:
                new_discussion = continue_discussion(user_input, st.session_state["discussion"])
                st.session_state["discussion"] += "\n" + new_discussion
        else:
            st.warning("発言を入力してください。")
    
    # 続きを話すボタンが押された場合の処理
    if continue_button:
        if st.session_state["discussion"]:
            default_input = "続きをお願いします。"
            new_discussion = continue_discussion(default_input, st.session_state["discussion"])
            st.session_state["discussion"] += "\n" + new_discussion
        else:
            st.warning("まずは会話を開始してください。")

# ------------------------
# 会話ウィンドウの表示（常に表示、会話内容がない場合はプレースホルダー表示）
# ------------------------
st.markdown('<div class="conversation">', unsafe_allow_html=True)
if st.session_state["discussion"]:
    display_line_style(st.session_state["discussion"])
else:
    st.markdown("<p style='color: gray;'>ここに会話が表示されます。</p>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
