import streamlit as st
import pandas as pd
import os
import base64
import json
import altair as alt
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import quote
from html import escape
import streamlit.components.v1 as components
from duckduckgo_search import DDGS

try:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None
    AIMessage = HumanMessage = SystemMessage = None



def resolve_app_password():
    """Try to load the app password from secrets, env vars, or fallback file."""
    secret = st.secrets.get('password')
    if isinstance(secret, str) and secret.strip():
        return secret.strip()

    env_password = os.getenv('STREAMLIT_APP_PASSWORD') or os.getenv('APP_PASSWORD')
    if env_password and env_password.strip():
        return env_password.strip()

    secrets_file = Path('.streamlit/secrets.toml')
    if secrets_file.exists():
        try:
            for line in secrets_file.read_text(encoding='utf-8').splitlines():
                stripped = line.strip()
                if stripped.startswith('password'):
                    _, raw_value = stripped.split('=', 1)
                    value = raw_value.strip().strip('"').strip("'")
                    if value:
                        return value
        except OSError:
            pass

    return None

# --- 비밀번호 기능 ---
def check_password():
    """비밀번호가 맞으면 True, 틀리면 False를 반환합니다."""
    try:
        # 비밀번호 입력 받기
        password = st.text_input("🔑 비밀번호를 입력하세요", type="password")
        st.markdown(
            "<p style='font-size:0.9rem; color:#6c757d; white-space:nowrap;'>⚠️ 비밀번호는 허가된 자만 사용 가능합니다. 보안을 유지하고, 무단 공개·허용 범위 밖 사용 시 법적 책임이 발생할 수 있습니다.</p>",
            unsafe_allow_html=True,
        )

        # .streamlit/secrets.toml에 설정된 비밀번호와 비교
        expected_password = resolve_app_password()
        if expected_password is None:
            st.error("🔐 비밀번호 설정이 필요합니다.")
            st.info("Streamlit Cloud에서 Secrets 편집기를 사용할 수 없다면 STREAMLIT_APP_PASSWORD/APP_PASSWORD 환경 변수를 지정하거나 .streamlit/secrets.toml 파일에 비밀번호를 직접 저장해야 합니다.")
            return False

        if password == expected_password:
            return True
        elif password: # 사용자가 무언가 입력은 했을 때
            st.error("😕 비밀번호가 틀렸습니다.")
            return False
        else: # 아직 아무것도 입력하지 않았을 때
            return False
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
        st.info("Streamlit Cloud에 배포하는 경우, 먼저 '.streamlit/secrets.toml' 파일에 비밀번호를 설정해야 합니다.")
        st.code("password = \"YOUR_PASSWORD\"","language=toml")
        return False

# --- 앱 시작 ---
if not check_password():
    st.stop() # 비밀번호가 맞지 않으면 앱 실행 중단

# --- 페이지 설정 ---
st.set_page_config(page_title="조합장 검색기", layout="wide")

def get_base64(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def set_background(png_file, overlay="rgba(0, 0, 0, 0.45)"):
    bin_str = get_base64(png_file)
    page_bg_img = f"""
    <style>
    .stApp {{
        background: linear-gradient({overlay}, {overlay}),
                    url("data:image/jpeg;base64,{bin_str}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    .stApp header {{
        background: transparent;
    }}
    </style>
    """
    st.markdown(page_bg_img, unsafe_allow_html=True)


def apply_theme(mode: str):
    """Apply light or dark theme tweaks for better readability."""
    normalized = (mode or "").lower()
    if normalized not in {"dark", "light"}:
        normalized = "light"

    if normalized == "dark":
        set_background("background.jpg", overlay="rgba(12, 20, 31, 0.72)")
        css = """
        <style>
        :root { color-scheme: dark; }
        .stApp {
            color: #e2e8f0 !important;
        }
        .stApp * {
            color: #e2e8f0 !important;
        }
        div[data-testid="stSidebar"] {
            background: rgba(15, 23, 42, 0.82);
        }
        div[data-testid="stSidebar"] * {
            color: #e2e8f0 !important;
        }
        .stTextInput input, .stSelectbox div[data-baseweb="select"] > div,
        .stNumberInput input, .stDateInput input, textarea {
            background: rgba(15, 23, 42, 0.55);
            color: #e2e8f0 !important;
            border-color: #334155 !important;
        }
        .stButton button, .stDownloadButton button {
            background: rgba(30, 64, 175, 0.65);
            color: #f8fafc !important;
            border: 1px solid #475569;
        }
        .stTabs [role="tablist"] button {
            color: #e2e8f0;
        }
        .stTabs [role="tablist"] button[aria-selected="true"] {
            border-bottom: 2px solid #60a5fa;
        }
        .stMetric label, .stMetric span {
            color: #f8fafc !important;
        }
        </style>
        """
    else:
        set_background("background.jpg", overlay="rgba(255, 255, 255, 0.95)")
        css = """
        <style>
        :root { color-scheme: light; }
        .stApp {
            color: #1f2937 !important;
            background-color: #f8fafc !important;
        }
        div[data-testid="stAppViewBlockContainer"],
        .st-emotion-cache-1wrcr25 {
            background-color: rgba(248, 250, 252, 0.96) !important;
        }
        div[data-testid="stDecoration"],
        div[data-testid="stStatusWidget"] {
            background-color: transparent !important;
        }
        .stApp * {
            color: #1f2937 !important;
        }
        div[data-testid="stSidebar"] {
            background: rgba(255, 255, 255, 0.9);
        }
        div[data-testid="stSidebar"] * {
            color: #1f2937 !important;
        }
        .stTextInput input, .stSelectbox div[data-baseweb="select"] > div,
        .stNumberInput input, .stDateInput input, textarea {
            background: rgba(255, 255, 255, 0.92);
            color: #1f2937 !important;
            border-color: #d1d5db !important;
        }
        .stButton button, .stDownloadButton button {
            background: rgba(59, 130, 246, 0.12);
            color: #1f2937 !important;
            border: 1px solid #93c5fd;
        }
        .stTabs [role="tablist"] button {
            color: #1f2937;
        }
        .stTabs [role="tablist"] button[aria-selected="true"] {
            border-bottom: 2px solid #2563eb;
        }
        h1, h2, h3, h4, h5, h6, label, p, span {
            text-shadow: 0 0 1px rgba(255, 255, 255, 0.6);
        }
        </style>
        """

    st.markdown(css, unsafe_allow_html=True)


def render_print_profile_component(row, info_pairs, photo_path):
    """Render a hidden HTML block and print button for exporting profile details."""
    name = str(row.get('성명', '') or '').strip()
    display_name = name if name else "조합장"
    title_text = f"{display_name}조합장 인적사항"
    coop_name = str(row.get('농축협명', '') or '').strip()

    rows_html = []
    for label, value in info_pairs:
        label_text = escape(str(label))
        value_text = escape(str(value))
        rows_html.append(f"<tr><th>{label_text}</th><td>{value_text}</td></tr>")
    rows_markup = "".join(rows_html)

    photo_html = ""
    if photo_path and os.path.exists(photo_path):
        try:
            with open(photo_path, "rb") as img_file:
                encoded_img = base64.b64encode(img_file.read()).decode()
            photo_html = (
                f"<div class='print-photo'><img src='data:image/jpeg;base64,{encoded_img}' "
                f"alt='{escape(display_name)} 사진'/></div>"
            )
        except OSError:
            photo_html = ""

    subtitle_html = (
        f"<p class='print-subtitle'>{escape(coop_name)}</p>" if coop_name else ""
    )

    content_html = (
        f"<div class='print-profile'>"
        f"<h1>{escape(title_text)}</h1>"
        f"{subtitle_html}"
        f"{photo_html}"
        f"<table class='print-table'><tbody>{rows_markup}</tbody></table>"
        f"</div>"
    )

    print_styles = """
    <style>
    @page {
        size: A4 portrait;
        margin: 15mm;
    }
    body {
        font-family: 'Pretendard','Noto Sans KR','Apple SD Gothic Neo',sans-serif;
        margin: 0;
        padding: 0;
        color: #111827;
        background: #ffffff;
    }
    .print-profile {
        width: 100%;
    }
    .print-profile h1 {
        font-size: 24px;
        margin: 0 0 8px 0;
        text-align: center;
    }
    .print-subtitle {
        text-align: center;
        margin: 0 0 20px 0;
        color: #4b5563;
        font-size: 14px;
    }
    .print-photo {
        text-align: center;
        margin-bottom: 18px;
    }
    .print-photo img {
        max-width: 120px;
        border-radius: 8px;
        box-shadow: 0 6px 16px rgba(15, 23, 42, 0.12);
    }
    .print-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
    }
    .print-table th,
    .print-table td {
        border: 1px solid #d1d5db;
        padding: 8px 10px;
        text-align: left;
        vertical-align: top;
    }
    .print-table th {
        width: 32%;
        background: #f3f4f6;
        font-weight: 600;
    }
    </style>
    """

    print_styles_json = json.dumps(print_styles, ensure_ascii=False)
    title_json = json.dumps(title_text, ensure_ascii=False)

    component_html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="utf-8" />
        <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: 'Pretendard','Noto Sans KR','Apple SD Gothic Neo',sans-serif;
            background: transparent;
        }}
        .control-wrapper {{
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            gap: 6px;
        }}
        .print-button {{
            background: linear-gradient(135deg, #f97316, #facc15);
            color: #ffffff;
            border: none;
            padding: 10px 18px;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 6px 14px rgba(249, 115, 22, 0.25);
        }}
        .print-button:hover {{
            background: linear-gradient(135deg, #fb923c, #fde047);
        }}
        .print-note {{
            font-size: 12px;
            color: #475569;
        }}
        </style>
    </head>
    <body>
        <div class="control-wrapper">
            <button class="print-button" onclick="printProfile()">PDF/인쇄</button>
            <span class="print-note">A4 용지 여백(15mm)으로 맞춰 저장·출력됩니다.</span>
        </div>
        <div id="print-target" style="display:none;">{content_html}</div>
        <script>
        const PRINT_STYLES = {print_styles_json};
        const TITLE_TEXT = {title_json};
        function printProfile() {{
            const target = document.getElementById('print-target');
            if (!target) {{
                alert('인쇄할 정보를 찾을 수 없습니다.');
                return;
            }}
            const printWindow = window.open('', '_blank', 'width=780,height=960');
            printWindow.document.write(`<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>${{TITLE_TEXT}}</title>${{PRINT_STYLES}}</head><body>${{target.innerHTML}}</body></html>`);
            printWindow.document.close();
            printWindow.focus();
            setTimeout(() => {{
                printWindow.print();
            }}, 400);
        }}
        </script>
    </body>
    </html>
    """
    components.html(component_html, height=110)


# --- AI 챗봇 유틸리티 ---

def resolve_openai_api_key():
    """Return the first available OpenAI API key from secrets, env vars, or fallback file."""
    runtime_key = st.session_state.get("runtime_openai_api_key")
    if isinstance(runtime_key, str) and runtime_key.strip():
        return runtime_key.strip()

    candidates = [
        st.secrets.get("openai_api_key"),
        st.secrets.get("OPENAI_API_KEY"),
        st.secrets.get("api_key"),
        os.getenv("OPENAI_API_KEY"),
        os.getenv("OPENAI_APIKEY"),
        os.getenv("OPENAI_KEY"),
    ]
    for value in candidates:
        if isinstance(value, str) and value.strip():
            return value.strip()

    secrets_file = Path(".streamlit/secrets.toml")
    if secrets_file.exists():
        try:
            for line in secrets_file.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.lower().startswith("openai_api_key"):
                    _, raw_value = stripped.split("=", 1)
                    value = raw_value.strip().strip('"').strip("'")
                    if value:
                        return value
        except OSError:
            pass

    return None


def _normalize_token(text: str) -> str:
    """Normalize tokens for fuzzy matching."""
    return re.sub(r"[\s\-\_/]", "", str(text or "")).lower()


def _next_export_key(prefix: str) -> str:
    """Return a unique key for export toolbars."""
    counter = st.session_state.get("_export_toolbar_counter", 0)
    st.session_state["_export_toolbar_counter"] = counter + 1
    return f"{prefix}-{counter}"


def render_export_toolbar(*args, **kwargs):
    """Export controls disabled per user request."""
    return


def render_dataframe_export_options(*args, **kwargs):
    """Export controls disabled per user request."""
    return


def fetch_duckduckgo_results(query: str, max_results: int = 5):
    """Return lightweight DuckDuckGo search results for the given query."""
    stripped = (query or "").strip()
    if not stripped:
        return []

    results = []
    try:
        with DDGS() as ddgs:
            for hit in ddgs.text(
                stripped,
                max_results=max_results,
                region="kr-kr",
                safesearch="moderate",
            ):
                title = hit.get("title") or hit.get("heading") or ""
                summary = hit.get("body") or hit.get("snippet") or ""
                url = hit.get("href") or hit.get("url") or ""
                if not (title and url):
                    continue
                results.append(
                    {
                        "title": title.strip(),
                        "summary": (summary or "").strip(),
                        "url": url.strip(),
                    }
                )
                if len(results) >= max_results:
                    break
    except Exception:
        return []
    return results


def format_search_results_for_prompt(results):
    """Create a concise text block from search results for LLM context."""
    if not results:
        return ""

    lines = []
    for idx, item in enumerate(results, 1):
        title = item.get("title", "")
        url = item.get("url", "")
        summary = item.get("summary", "")
        if summary and len(summary) > 180:
            summary = summary[:177] + "..."
        lines.append(f"{idx}. {title} - {url}")
        if summary:
            lines.append(f"   요약: {summary}")
    return "\n".join(lines)


def _format_field_value(value):
    """Format values for compact prompt injection."""
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if pd.isna(value):
            return None
        if float(value).is_integer():
            return str(int(value))
        return str(round(float(value), 2))
    if pd.isna(value):
        return None
    return str(value)


def build_reference_records(question, df, max_matches=3):
    """Return up to `max_matches` rows from df that look relevant to the question."""
    if not question:
        return []

    normalized_question = _normalize_token(question)
    if not normalized_question:
        return []

    dataframes = []
    name_norm_col = "정제성명"
    coop_norm_col = "정제농축협명"

    if name_norm_col in df.columns:
        mask = df[name_norm_col].astype(str).str.contains(normalized_question, case=False, na=False)
        if mask.any():
            dataframes.append(df[mask])

    if coop_norm_col in df.columns:
        mask = df[coop_norm_col].astype(str).str.contains(normalized_question, case=False, na=False)
        if mask.any():
            dataframes.append(df[mask])

    combined = pd.concat(dataframes, axis=0).drop_duplicates() if dataframes else pd.DataFrame()

    if combined.empty:
        tokens = [token for token in re.findall(r"[가-힣A-Za-z0-9]+", question) if len(token) >= 2]
        token_matches = []
        for token in tokens:
            token_mask = pd.Series(False, index=df.index)
            for col in ("성명", "농축협명", "주요경력", "상임구분", "선수", "부가의결권"):
                if col in df.columns:
                    token_mask |= df[col].astype(str).str.contains(token, case=False, na=False)
            if token_mask.any():
                token_matches.append(df[token_mask])
        if token_matches:
            combined = pd.concat(token_matches, axis=0).drop_duplicates()

    if combined.empty:
        return []

    return combined.head(max_matches).to_dict(orient="records")


def format_records_for_prompt(records):
    """Convert retrieved records into a compact plaintext block for LLM context."""
    if not records:
        return ""

    field_order = [
        "성명", "농축협명", "유형", "상임구분",
        "주요경력", "연락처", "임기시작일", "임기만료일",
        "선수", "부가의결권", "비고",
    ]

    field_labels = {
        "성명": "성명",
        "농축협명": "소속 조합",
        "유형": "유형",
        "상임구분": "상임 구분",
        "주요경력": "주요 경력",
        "연락처": "연락처",
        "임기시작일": "임기 시작일",
        "임기만료일": "임기 만료일",
        "선수": "선수",
        "부가의결권": "부가 의결권",
        "비고": "비고",
    }

    formatted_rows = []
    for record in records:
        parts = []
        for field in field_order:
            if field in record:
                value = _format_field_value(record[field])
                if value:
                    parts.append(f"{field_labels.get(field, field)}: {value}")
        if parts:
            formatted_rows.append("\n".join(parts))

    return "\n\n".join(formatted_rows)


def compose_system_prompt():
    """Return the default system prompt for the AI chatbot."""
    return (
        "당신은 대한민국 농업·농촌·농협(농협중앙회 포함)에 대해 사실만을 전달하는 상담원입니다. "
        "다음 기준을 반드시 지키세요:\n"
        "1) 내부 조합장 데이터 혹은 제공된 외부 검색 결과에서 확인된 사실만 말합니다.\n"
        "2) 주관적 평가·칭찬·비판·추측·계획 등은 하지 않습니다. 가능성이나 의견을 말하지 않습니다.\n"
        "3) 근거를 명확히 밝히세요. 내부 데이터면 '조합장 현황 자료 기준'이라고, 검색 결과면 제목과 URL을 표시하세요.\n"
        "4) 자료가 없으면 '자료에 없음' 또는 '검색 결과 없음'이라고 명확히 말합니다.\n"
        "5) 개인정보나 민감 정보는 노출하지 않습니다.\n"
        "6) 답변은 간결한 문장이나 목록 형태로 작성하고, 출처가 서로 다르면 구분해 주세요."
    )


def generate_structured_answer(question, df):
    """Return a deterministic answer for recognizable queries plus related records."""
    normalized = _normalize_token(question)
    lowered = question.lower()

    # 부가의결권 관련 질의 처리
    if "부가의결권" in normalized or "추가의결권" in normalized:
        column = "부가의결권"
        if column in df.columns:
            value_series = df[column].astype(str).str.strip()
            has_rights = (
                df[column].notna()
                & (value_series != "")
                & ~value_series.str.contains("없", na=False)
            )
            subset = df.loc[has_rights].copy()
            if subset.empty:
                return "현재 자료에서 부가의결권이 기재된 조합은 확인되지 않습니다.", []

            grouped = (
                subset.groupby("농축협명")
                .agg(
                    조합장수=("성명", "count"),
                    조합장목록=(
                        "성명",
                        lambda values: ", ".join(
                            sorted(
                                {str(value).strip() for value in values if str(value).strip()}
                            )
                        ),
                    ),
                )
                .reset_index()
            )

            bullet_lines = [
                f"- {row['농축협명']}: {row['조합장수']}명 ({row['조합장목록']})"
                for _, row in grouped.iterrows()
            ]
            summary = (
                f"부가의결권이 기재된 조합은 총 {len(grouped)}곳이며, 조합장 {subset.shape[0]}명이 있습니다.\n"
                "자세한 목록은 다음과 같습니다:\n"
                + "\n".join(bullet_lines)
            )

            record_columns = [
                col
                for col in ["성명", "농축협명", "부가의결권", "임기시작일", "임기만료일"]
                if col in subset.columns
            ]
            return summary, subset[record_columns].to_dict(orient="records")

    # 최연장자 / 나이에 대한 질문 처리
    age_keywords = ("최연장", "가장나이가", "나이가가장", "최고령", "연장자")
    if any(keyword in normalized for keyword in age_keywords) or "나이가 많은" in lowered:
        year_column = "출생연도"
        if year_column in df.columns:
            numeric_birth = pd.to_numeric(df[year_column], errors="coerce")
            valid_all = df.loc[~numeric_birth.isna()].copy()
            if valid_all.empty:
                return "자료에 출생연도가 기재된 행이 없어 최연장 조합장을 파악하기 어렵습니다.", []

            valid_all["__birth_year"] = numeric_birth.loc[valid_all.index].astype(int)
            current_year = datetime.now().year
            valid = valid_all[
                (valid_all["__birth_year"] >= 1900) & (valid_all["__birth_year"] <= current_year)
            ]
            if not valid.empty:
                oldest_year = int(valid["__birth_year"].min())
                oldest = valid[valid["__birth_year"] == oldest_year]
                approx_age = current_year - oldest_year

                names = ", ".join(oldest["성명"].astype(str))
                unions = ", ".join(oldest["농축협명"].astype(str))

                answer = (
                    f"데이터상 가장 나이가 많은 조합장은 {oldest_year}년생인 {names} (소속: {unions})입니다."
                )
                if approx_age > 0:
                    answer += f" {current_year}년 기준으로 만 {approx_age}세 정도로 추정됩니다."

                record_columns = [
                    col
                    for col in [
                        "성명",
                        "농축협명",
                        "출생연도",
                        "상임구분",
                        "임기시작일",
                        "임기만료일",
                        "주요경력",
                    ]
                    if col in oldest.columns
                ]
                return answer, oldest[record_columns].to_dict(orient="records")

            return "출생연도가 확인 가능한 범위를 벗어나 최연장 조합장을 계산하기 어렵습니다.", []

        return "자료에 출생연도가 정리되어 있지 않아 최연장 조합장을 특정하기 어렵습니다.", []

    return None, []


DEFAULT_THEME = "light"

if "ui_theme" not in st.session_state:
    st.session_state.ui_theme = DEFAULT_THEME

with st.sidebar:
    st.sidebar.markdown("### 🎨 화면 모드")
    theme_choice = st.radio(
        "배경 모드",
        ("밝은 모드", "어두운 모드"),
        index=0 if st.session_state.ui_theme == "light" else 1,
        label_visibility="collapsed",
        key="theme_selector",
    )
    st.sidebar.divider()

st.session_state.ui_theme = "dark" if theme_choice == "어두운 모드" else "light"
apply_theme(st.session_state.ui_theme)


def show_chatbot_page(df):
    """Render the AI chatbot interface."""
    st.title("AI 챗봇 상담")
    st.caption("조합장 데이터 기반으로 간단한 질문에 답변하거나 비교 정보를 알려드립니다.")

    api_key = resolve_openai_api_key()
    if not api_key:
        st.error("OpenAI API 키가 설정되지 않았습니다.")
        with st.expander("여기에 OpenAI API 키를 입력하세요", expanded=True):
            entered_key = st.text_input(
                "OpenAI API 키",
                type="password",
                placeholder="sk-...",
            )
            if st.button("임시로 사용하기", use_container_width=True):
                if entered_key and entered_key.strip():
                    st.session_state["runtime_openai_api_key"] = entered_key.strip()
                    st.success("API 키가 임시로 저장되었습니다. 질문을 다시 입력해 주세요.")
                    st.experimental_rerun()
                else:
                    st.warning("유효한 API 키를 입력해 주세요.")
        st.info(
            "이 입력은 현재 브라우저 세션에서만 사용됩니다. "
            "영구적으로 저장하려면 `.streamlit/secrets.toml` 또는 `OPENAI_API_KEY` 환경 변수를 설정해 주세요."
        )
        return

    if ChatOpenAI is None or AIMessage is None:
        st.error("필요한 LangChain/OpenAI 모듈을 찾을 수 없습니다.")
        st.info("가상환경에서 `pip install -r requirements.txt`를 실행해 패키지를 설치해 주세요.")
        return

    if "ai_chat_messages" not in st.session_state:
        st.session_state.ai_chat_messages = [
            {"role": "assistant", "content": "안녕하세요! 조합장 정보에 대해 무엇이든 물어보세요."}
        ]

    model_name = st.secrets.get("openai_model") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"

    for message in st.session_state.ai_chat_messages:
        role = "assistant" if message["role"] == "assistant" else "user"
        with st.chat_message(role):
            st.markdown(message["content"])

    user_prompt = st.chat_input("질문을 입력해 주세요.")
    if not user_prompt:
        return

    st.session_state.ai_chat_messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    structured_answer, structured_records = generate_structured_answer(user_prompt, df)
    if structured_answer:
        st.session_state.ai_chat_messages.append({"role": "assistant", "content": structured_answer})
        with st.chat_message("assistant"):
            st.markdown(structured_answer)
            render_export_toolbar(
                structured_answer,
                prefix="chatbot-structured-text",
                file_name="chatbot_response.txt",
                copy_label="📋 답변 복사",
                print_label="🖨️ 답변 인쇄",
                save_label="💾 TXT 저장",
                heading="AI 답변 내보내기",
            )

        if structured_records:
            with st.expander("참고로 사용된 데이터 보기", expanded=False):
                display_records = pd.DataFrame(structured_records)
                if not display_records.empty:
                    show_columns = [
                        col
                        for col in [
                            "성명",
                            "농축협명",
                            "부가의결권",
                            "출생연도",
                            "상임구분",
                            "임기시작일",
                            "임기만료일",
                            "주요경력",
                        ]
                        if col in display_records.columns
                    ]
                    st.dataframe(display_records[show_columns] if show_columns else display_records)
                    render_dataframe_export_options(
                        display_records[show_columns] if show_columns else display_records,
                        "chatbot_reference",
                        heading="참고 데이터 내보내기",
                    )
                else:
                    st.write("표시할 참고 데이터가 없습니다.")

        search_results = fetch_duckduckgo_results(user_prompt, max_results=5)
        if search_results:
            with st.expander("외부 검색 결과 (DuckDuckGo)", expanded=False):
                for item in search_results:
                    summary = item.get("summary") or "요약 정보가 없습니다."
                    st.markdown(f"- [{item['title']}]({item['url']})\n  {summary}")
        return

    with st.spinner("AI가 자료를 확인하고 있습니다..."):
        try:
            model = ChatOpenAI(
                api_key=api_key,
                model=model_name,
                temperature=0.2,
                max_tokens=600,
            )
        except Exception as exc:
            st.error(f"모델을 초기화하는 중 오류가 발생했습니다: {exc}")
            return

        reference_records = build_reference_records(user_prompt, df)
        context_block = format_records_for_prompt(reference_records)
        search_results = []
        search_needed = not reference_records or bool(re.search(r"(뉴스|기사|보도|소식|동향|최근|최신)", user_prompt))
        if search_needed:
            search_results = fetch_duckduckgo_results(user_prompt, max_results=5)
        search_context_block = format_search_results_for_prompt(search_results)

        messages = [SystemMessage(content=compose_system_prompt())]
        for past in st.session_state.ai_chat_messages[:-1]:
            if past["role"] == "user":
                messages.append(HumanMessage(content=past["content"]))
            else:
                messages.append(AIMessage(content=past["content"]))

        latest_user_content = user_prompt
        if context_block:
            latest_user_content = (
                f"{user_prompt}\n\n[참고 데이터]\n{context_block}\n\n"
                "위 정보를 우선 활용해서 답변해 주세요."
            )
        if search_context_block:
            latest_user_content = (
                f"{latest_user_content}\n\n[외부 검색 결과]\n{search_context_block}\n\n"
                "필요하다면 위의 외부 검색 결과를 참고해 주세요."
            )
        messages.append(HumanMessage(content=latest_user_content))

        try:
            response = model.invoke(messages)
            assistant_reply = response.content if hasattr(response, "content") else str(response)
        except Exception as exc:
            st.error(f"AI 응답 생성 중 오류가 발생했습니다: {exc}")
            return

    st.session_state.ai_chat_messages.append({"role": "assistant", "content": assistant_reply})
    with st.chat_message("assistant"):
        st.markdown(assistant_reply)
        render_export_toolbar(
            assistant_reply,
            prefix="chatbot-ai-text",
            file_name="chatbot_response.txt",
            copy_label="📋 답변 복사",
            print_label="🖨️ 답변 인쇄",
            save_label="💾 TXT 저장",
            heading="AI 답변 내보내기",
        )

    if context_block:
        with st.expander("참고로 사용된 데이터 보기", expanded=False):
            display_records = pd.DataFrame(reference_records)
            if not display_records.empty:
                show_columns = [col for col in [
                    "성명", "농축협명", "유형", "주요경력", "연락처",
                    "임기시작일", "임기만료일", "상임구분", "선수", "부가의결권", "비고"
                ] if col in display_records.columns]
                st.dataframe(display_records[show_columns])
                render_dataframe_export_options(
                    display_records[show_columns],
                    "chatbot_reference",
                    heading="참고 데이터 내보내기",
                )
            else:
                st.write("표시할 참고 데이터가 없습니다.")

    if search_results:
        with st.expander("외부 검색 결과 (DuckDuckGo)", expanded=False):
            for item in search_results:
                summary = item.get("summary") or "요약 정보가 없습니다."
                st.markdown(f"- [{item['title']}]({item['url']})\n  {summary}")


# --- 데이터 로딩 ---
EXCEL_FILENAME = "조합장 현황.xlsx"

@st.cache_data(ttl=0)
def load_data():
    df = pd.read_excel(EXCEL_FILENAME, engine='openpyxl')
    df['정제성명'] = df['성명'].astype(str).str.replace(' ', '').str.strip()
    df['정제농축협명'] = df['농축협명'].astype(str).str.replace(' ', '').str.strip()
    return df

df = load_data()

# --- 페이지 함수 ---

def show_search_page(df):
    """조합장 정보 검색 페이지를 표시합니다."""
    st.title("🧑‍🌾 조합장 정보 검색기")
    st.write("검색 기준을 선택한 뒤 성명 또는 농축협명으로 조합장 정보를 조회할 수 있습니다.")

    # --- 상태 관리 ---
    if 'results' not in st.session_state:
        st.session_state.results = None
    if 'query' not in st.session_state:
        st.session_state.query = ""
    # --- 상태 관리 끝 ---

    # ✅ 검색 UI
    search_option = st.radio("검색 기준 선택", ["성명", "농축협명"], horizontal=True)
    query = st.text_input(f"🔍 {search_option} 입력", st.session_state.query)

    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("검색하기"):
            if query:
                search_text = query.replace('\n', '').replace('\r', '').replace(' ', '').strip()
                if search_option == "성명":
                    results = df[df['정제성명'] == search_text]
                else:
                    results = df[df['정제농축협명'].str.contains(f'^{search_text}$', regex=True)]
                st.session_state.results = results
                st.session_state.query = query
            else:
                st.session_state.results = None
                st.session_state.query = ""
            st.rerun()

    with col2:
        if st.button("초기화"):
            st.session_state.results = None
            st.session_state.query = ""
            st.rerun()

    # ✅ 검색 결과 표시
    if st.session_state.results is not None:
        results = st.session_state.results
        if results.empty:
            st.warning(f"입력하신 '{st.session_state.query}'에 해당하는 조합장을 찾을 수 없습니다.")
        else:
            st.success(f"🔎 '{st.session_state.query}'에 대한 총 {len(results)}명의 결과가 검색되었습니다.")
            for idx, row in results.iterrows():
                st.markdown(f"### 📋 [{row['성명']}] 조합장")
                tab1, tab2 = st.tabs(["상세 정보", "최신 뉴스"])
                with tab1:
                    photo_path = f"photo/{row['순번']}.jpg"
                    if os.path.exists(photo_path):
                        st.image(photo_path, caption=f"{row['성명']} 조합장 사진", width=180)
                    else:
                        st.info("📁 등록된 사진이 없습니다.")

                    info_data = []
                    printable_pairs = []
                    for col in df.columns:
                        if col in ['정제성명', '정제농축협명']:
                            continue
                        value = row[col]
                        if col == '출생년도' and pd.notna(value):
                            try: value = int(float(value))
                            except (ValueError, TypeError): pass
                        if col in ['임기시작일', '임기만료일']:
                            v = pd.to_datetime(value, errors='coerce') if not pd.to_numeric(str(value).strip(), errors='coerce') else pd.to_datetime(pd.to_numeric(str(value).strip(), errors='coerce'), origin='1899-12-30', unit='D', errors='coerce')
                            if pd.notna(v): value = v.strftime('%Y-%m-%d')
                        if pd.isnull(value): value = "정보 없음"
                        display_value = str(value)
                        info_data.append([col, display_value])
                        printable_pairs.append((col, display_value))

                    info_df = pd.DataFrame(info_data, columns=["항목", "내용"])
                    st.table(info_df.set_index("항목"))
                    render_print_profile_component(row, printable_pairs, photo_path)

                with tab2:
                    search_query = f"{row['농축협명']} {row['성명']}"
                    encoded_query = quote(search_query)
                    st.write(f"아래 링크를 클릭하면 '{search_query}'에 대한 뉴스 검색 결과가 새 탭에서 열립니다.")
                    st.divider()
                    st.markdown(f"📰 [Google 뉴스 검색](https://news.google.com/search?q={encoded_query})")
                    st.markdown(f"📰 [네이버 뉴스 검색](https://search.naver.com/search.naver?where=news&query={encoded_query})")
                    st.markdown(f"📰 [다음 뉴스 검색](https://search.daum.net/search?w=news&q={encoded_query})")
                st.markdown("-----")

def show_analysis_page(df):
    """데이터 통계 분석 페이지를 표시합니다."""
    st.title("📊 통계 자료")
    st.write("엑셀 파일의 특정 컬럼을 선택하여 데이터 분포를 확인합니다.")

    # 분석할 컬럼 선택
    columns = ['순번', '시도', '시군', '농축협명', '유형', '성명', '출생연도', '주요경력', '연락처', '임기시작일', '임기만료일', '상임구분', '선수', '부가의결권', '비고']
    # 사용자가 분석에 의미있는 컬럼을 선택하도록 유도
    default_cols = ['시도', '시군', '유형', '상임구분', '선수']
    analyzable_columns = [col for col in columns if col in default_cols or (df[col].nunique() < 50 and df[col].nunique() > 1)] # 유니크 값이 너무 많거나 1개인 컬럼 제외
    
    selected_column = st.selectbox("분석할 컬럼을 선택하세요", analyzable_columns)

    if selected_column:
        st.markdown(f"### 📈 **{selected_column}** 컬럼 데이터 분포")
        
        # 데이터 집계
        value_counts = df[selected_column].value_counts().rename_axis(selected_column).reset_index(name="count")

        # 많은 카테고리가 있을 경우 상위 일부만 선택할 수 있도록 옵션 제공
        max_items = len(value_counts)
        top_n = max_items
        if max_items > 10:
            show_all = st.checkbox(f"전체 {max_items}개 항목 모두 보기", value=False)
            if not show_all:
                default_top = min(20, max_items)
                slider_min = 5 if max_items >= 5 else 1
                top_n = st.slider("표시할 항목 수", min_value=slider_min, max_value=max_items, value=default_top, step=1)
        value_counts = value_counts.sort_values("count", ascending=False).head(top_n)

        # 데이터 표현 방식 선택 (절대값 / 비율)
        display_mode = st.radio("표시 방식", ("건수", "비율(%)"), horizontal=True)
        total = value_counts["count"].sum()
        value_counts["percentage"] = (value_counts["count"] / total * 100).round(2) if total else 0

        if display_mode == "건수":
            y_field = "count"
            y_title = "건수"
        else:
            y_field = "percentage"
            y_title = "비율 (%)"

        chart_data = value_counts.copy()
        y_max = chart_data[y_field].max() if not chart_data.empty else 0

        chart = (
            alt.Chart(chart_data)
            .mark_bar(size=20)
            .encode(
                x=alt.X(f"{selected_column}:N", sort="-y", title=selected_column),
                y=alt.Y(f"{y_field}:Q", title=y_title,
                        scale=alt.Scale(domain=(0, y_max * 1.1 if y_max else 1))),
                tooltip=[
                    alt.Tooltip(f"{selected_column}:N", title=selected_column),
                    alt.Tooltip("count:Q", title="건수"),
                    alt.Tooltip("percentage:Q", title="비율 (%)"),
                ],
            )
            .properties(height=400)
        )

        col1, col2 = st.columns(2)
        with col1:
            st.write("**막대 그래프**")
            st.altair_chart(chart, use_container_width=True)

        with col2:
            st.write("**데이터 표**")
            display_cols = [selected_column, "count", "percentage"]
            display_df = chart_data[display_cols].rename(columns={"count": "건수", "percentage": "비율(%)"})
            st.dataframe(display_df)

        export_prefix = _normalize_token(selected_column) or "column"
        summary_lines = [f"[{selected_column}] 분포 (상위 {len(chart_data)}건)"]
        for _, row in chart_data.iterrows():
            count_value = row.get("count", 0)
            try:
                count_display = int(count_value)
            except (TypeError, ValueError):
                count_display = count_value
            percentage_value = row.get("percentage", 0)
            try:
                percentage_display = f"{float(percentage_value):.2f}"
            except (TypeError, ValueError):
                percentage_display = str(percentage_value)
            summary_lines.append(f"- {row.get(selected_column, '미기재')}: {count_display}건 ({percentage_display}%)")

        summary_text = "\n".join(summary_lines)
        render_export_toolbar(
            summary_text,
            prefix=f"analysis-summary-{export_prefix}",
            file_name=f"{export_prefix}_summary.txt",
            copy_label="📋 요약 복사",
            print_label="🖨️ 요약 인쇄",
            save_label="💾 TXT 저장",
            heading="요약 내보내기",
        )
        render_dataframe_export_options(display_df, f"{export_prefix}_analysis")


# --- 사이드바 및 메인 로직 ---



# --- 사이드바 및 메인 로직 ---
st.sidebar.title("메뉴")
menu_options = ("조합장 정보 검색", "통계 자료", "AI 챗봇")
menu = st.sidebar.radio("원하는 작업을 선택하세요", menu_options)

if menu == "조합장 정보 검색":
    show_search_page(df)
elif menu == "통계 자료":
    show_analysis_page(df)
else:
    show_chatbot_page(df)


