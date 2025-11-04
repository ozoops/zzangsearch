import streamlit as st
import pandas as pd
import os
import base64
import json
import altair as alt
from pathlib import Path
from datetime import datetime
from urllib.parse import quote
from html import escape
import streamlit.components.v1 as components
import openai


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

def set_background(png_file):
    bin_str = get_base64(png_file)
    page_bg_img = f"""
    <style>
    .stApp {{
        background: linear-gradient(rgba(0, 0, 0, 0.45), rgba(0, 0, 0, 0.45)),
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

set_background('background.jpg')


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
            st.dataframe(chart_data[display_cols].rename(columns={"count": "건수", "percentage": "비율(%)"}))


# --- 사이드바 및 메인 로직 ---
def _sanitize_api_error(msg: str) -> str:
    """Redact any OpenAI-style API keys from error messages."""
    return re.sub(r"sk-[A-Za-z0-9\-]+", "sk-***", msg)


def show_chatbot_page(df):
    """AI 챗봇을 통해 데이터에 대해 질문하는 페이지를 표시합니다."""
    st.title("🤖 AI 챗봇에게 질문하기")
    st.write("조합장 데이터에 대해 궁금한 점을 자유롭게 질문해보세요.")
    st.markdown(
        """
        <style>
        .chatbot-example-box {
            background: rgba(255, 255, 255, 0.9);
            color: #1f2937;
            padding: 14px 18px;
            border-radius: 12px;
            font-size: 0.95rem;
            line-height: 1.6;
            border: 1px solid rgba(15, 23, 42, 0.08);
            box-shadow: 0 8px 18px rgba(15, 23, 42, 0.12);
            backdrop-filter: blur(6px);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='chatbot-example-box'>예시: '서울시에 있는 조합장 목록 보여줘', '조합장 수가 가장 많은 시도는 어디야?', '가장 젊은 조합장은 누구이고 소속은 어디야?'</div>",
        unsafe_allow_html=True,
    )

    # --- OpenAI API 키 확인 ---
    raw_api_key = st.secrets.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
    openai_api_key = raw_api_key.strip() if isinstance(raw_api_key, str) else None
    raw_project = (
        st.secrets.get("openai_project")
        or os.getenv("OPENAI_PROJECT")
        or os.getenv("OPENAI_PROJECT_ID")
    )
    openai_project = raw_project.strip() if isinstance(raw_project, str) else None
    if not openai_api_key:
        st.error("⚠️ OpenAI API 키가 설정되지 않았습니다.")
        st.info("`.streamlit/secrets.toml` 파일에 `openai_api_key = \"YOUR_API_KEY\"` 형식으로 API 키를 추가하거나, `OPENAI_API_KEY` 환경 변수를 설정해주세요.")
        st.stop()

    # --- LangChain 에이전트 초기화 ---
    from langchain_openai import ChatOpenAI
    from langchain.agents.agent_types import AgentType
    from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent

    default_headers = {"OpenAI-Project": openai_project} if openai_project else None

    llm = ChatOpenAI(
        temperature=0,
        model="gpt-4",
        openai_api_key=openai_api_key,
        streaming=True,
        default_headers=default_headers,
    )
    
    # '정제'된 컬럼은 사용자에게 혼동을 줄 수 있으므로 제외하고 원본 컬럼만 사용
    agent_df = df.drop(columns=['정제성명', '정제농축협명'])
    
    agent = create_pandas_dataframe_agent(
        llm,
        agent_df,
        verbose=True,
        agent_type=AgentType.OPENAI_FUNCTIONS,
        handle_parsing_errors=True,
        allow_dangerous_code=True, # PandasAgent requires this
        agent_executor_kwargs={"handle_parsing_errors": True},
        prompt_suffix="모든 답변은 한국어로 해주세요."
    )

    # --- 채팅 UI ---
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("질문을 입력하세요..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("AI가 답변을 생성 중입니다..."):
                try:
                    response = agent.invoke(prompt)
                    st.markdown(response["output"])
                    st.session_state.messages.append({"role": "assistant", "content": response["output"]})
                except openai.AuthenticationError:
                    st.error("❌ OpenAI API 키가 올바르지 않거나 비활성화되었습니다. 키의 유효성을 다시 확인해주세요.")
                except Exception as e:
                    st.error(f"답변 생성 중 오류가 발생했습니다: {e}")


# --- 사이드바 및 메인 로직 ---
st.sidebar.title("메뉴")
menu_options = ("조합장 정보 검색", "통계 자료", "🤖 AI 챗봇")
menu = st.sidebar.radio("원하는 작업을 선택하세요", menu_options)

if menu == "조합장 정보 검색":
    show_search_page(df)
elif menu == "통계 자료":
    show_analysis_page(df)
elif menu == "🤖 AI 챗봇":
    show_chatbot_page(df)

