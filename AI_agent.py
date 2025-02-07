import streamlit as st
import requests
import re
import random

# ========================
#    定数／設定
# ========================
# st.secrets を利用して API キーを隠す（.streamlit/secrets.toml に記述）
API_KEY = st.secrets["general"]["api_key"]
MODEL_NAME = "gemini-1.5-flash"
# 固定の日本人キャラクター名
NAMES = ["ゆかり", "しんや", "みのる"]

# ========================
#    関数定義
# ========================

def analyze_question(question: str) -> int:
    """質問内容から感情／論理キーワードをもとにスコアを算出"""
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
    """
    質問内容に応じて、各キャラクターのスタイルと詳細文を調整する。
    """
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
    """
    モデルが返す不要なJSON形式（例: 'parts': [{'text': ...}], 'role': 'model'）を除去する。
    """
    if not isinstance(text, str):
        text = str(text) if text else ""
    pattern = r"'parts': \[\{'text':.*?\}\], 'role': 'model'"
    cleaned = re.sub(pattern, "", text, flags=re.DOTALL)
    return cleaned.strip()

def call_gemini_api(prompt: str) -> str:
    """
    gemini-1.5-flash モデルを呼び出し、指定されたプロンプトに基づく回答または会話文を取得する。
    'content' が dict 型の場合は、parts 内のテキストを連結して返す。
    """
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
    """
    ユーザーの質問と各キャラクターの設定情報をもとに、3人が自然な会話をするプロンプトを生成し、結果を返す。
    出力形式は「ゆかり: 発言内容」「しんや: 発言内容」「みのる: 発言内容」。
    """
    prompt = f"【ユーザーの質問】\n{question}\n\n"
    for name, params in persona_params.items():
        prompt += f"{name}は【{params['style']}な視点】で、{params['detail']}。\n"
    prompt += (
        "\n上記情報をもとに、3人が友達同士のように自然な会話をしてください。\n"
        "出力形式は以下の通りです。\n"
        "ゆかり: 発言内容\n"
        "しんや: 発言内容\n"
        "みのる: 発言内容\n"
        "余計なJSON形式は入れず、自然な日本語の会話のみを出力してください。"
    )
    return call_gemini_api(prompt)

def generate_summary(discussion: str) -> str:
    """
    生成された3人の会話全体をもとに、質問に対するまとめ回答を生成するプロンプトを作成し、結果を返す。
    """
    prompt = (
        "以下は3人の会話内容です。\n"
        f"{discussion}\n\n"
        "上記の会話を踏まえて、質問に対するまとめ回答を生成してください。\n"
        "自然な日本語文で出力し、余計なJSON形式は不要です。"
    )
    return call_gemini_api(prompt)

def display_line_style(text: str):
    """
    会話の各行を改行で分割し、LINE風の吹き出し形式で表示する。
    文字色は濃い灰色（#333）で、フォントは Arial, sans-serif を指定。
    """
    lines = text.split("\n")
    color_map = {
        "ゆかり": {"bg": "#DCF8C6", "color": "#333"},
        "しんや": {"bg": "#E0F7FA", "color": "#333"},
        "みのる": {"bg": "#FCE4EC", "color": "#333"}
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
st.title("ぼくのともだち")

# --- 質問入力エリア ---
question = st.text_area("質問を入力してください", placeholder="例: 官民共創施設の名前を考えてください。", height=150)

# セッション状態の初期化
if "discussion" not in st.session_state:
    st.session_state["discussion"] = ""
if "summary" not in st.session_state:
    st.session_state["summary"] = ""

# --- 会話生成ボタン ---
if st.button("会話を開始"):
    if question.strip():
        persona_params = adjust_parameters(question)
        discussion = generate_discussion(question, persona_params)
        st.session_state["discussion"] = discussion  # 会話履歴として保存
        st.write("### 3人の会話")
        display_line_style(discussion)
    else:
        st.warning("質問を入力してください。")

# --- まとめ回答生成ボタン ---
if st.button("会話をまとめる"):
    if st.session_state["discussion"]:
        summary = generate_summary(st.session_state["discussion"])
        st.session_state["summary"] = summary
        st.write("### まとめ回答")
        st.markdown(f"**まとめ:** {summary}")
    else:
        st.warning("まずは会話を開始してください。")
