import streamlit as st
import pandas as pd
import os
import base64
import json
import io
import altair as alt
import gspread
import re
from collections.abc import Mapping
from pathlib import Path
from datetime import datetime
from urllib.parse import quote
from html import escape
import streamlit.components.v1 as components
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload



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


def as_plain_dict(value):
    """Best-effort convert Streamlit config sections to plain dicts."""
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, dict):
        return value
    return {}


def load_service_account_info():
    """Load Google service-account credentials from secrets, env vars, or local file."""
    secrets_info = as_plain_dict(st.secrets.get("gdrive_service_account"))
    if secrets_info.get("private_key"):
        return secrets_info

    raw_json = st.secrets.get("gdrive_service_account_json")
    if isinstance(raw_json, str) and raw_json.strip():
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError:
            pass

    path_hint = st.secrets.get("gdrive_service_account_file")
    candidate_paths = []
    if isinstance(path_hint, str) and path_hint.strip():
        candidate_paths.append(Path(path_hint.strip()))
    candidate_paths.append(Path(".streamlit/gdrive_service_account.json"))

    for candidate in candidate_paths:
        try:
            if candidate.exists():
                return json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

    env_json = os.getenv("GDRIVE_SERVICE_ACCOUNT_JSON")
    if env_json:
        try:
            return json.loads(env_json)
        except json.JSONDecodeError:
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
        div[data-testid="stTable"] tbody tr th,
        div[data-testid="stTable"] tbody tr td:first-child {
            white-space: nowrap !important;
            word-break: keep-all;
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
        div[data-testid="stTable"] tbody tr th,
        div[data-testid="stTable"] tbody tr td:first-child {
            white-space: nowrap !important;
            word-break: keep-all;
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


def _normalize_token(text: str) -> str:
    """Normalize tokens for fuzzy matching."""
    return re.sub(r"[\s\-\_/]", "", str(text or "")).lower()


def format_year_value(value):
    """Return a clean year string if possible."""
    if pd.isna(value):
        return "정보 없음"

    numeric = pd.to_numeric(str(value).strip(), errors="coerce")
    if pd.notna(numeric):
        try:
            return str(int(numeric))
        except (ValueError, TypeError):
            pass

    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text or "정보 없음"


def format_date_value(value):
    """Return YYYY-MM-DD if convertible, otherwise original string."""
    if pd.isna(value):
        return "정보 없음"

    raw = str(value).strip()
    if not raw:
        return "정보 없음"

    parsed = pd.to_datetime(raw, errors="coerce")
    if pd.notna(parsed):
        return parsed.strftime("%Y-%m-%d")

    numeric = pd.to_numeric(raw, errors="coerce")
    if pd.notna(numeric):
        parsed = pd.to_datetime(
            numeric, origin="1899-12-30", unit="D", errors="coerce"
        )
        if pd.notna(parsed):
            return parsed.strftime("%Y-%m-%d")

    return raw


def download_excel_from_drive(creds_info, file_id: str, logs: list, worksheet: str | int | None = None):
    """Download an Excel or Google Sheet file from Drive and return a DataFrame."""
    if not creds_info or not file_id:
        return None

    scopes = ["https://www.googleapis.com/auth/drive.readonly"]
    try:
        creds = service_account.Credentials.from_service_account_info(
            creds_info,
            scopes=scopes,
        )
        service = build("drive", "v3", credentials=creds)
        logs.append("Drive API: 서비스 빌드 성공. 파일 메타데이터 요청 중...")
        metadata = service.files().get(fileId=file_id, fields="mimeType,name").execute()
        mime_type = metadata.get("mimeType", "")
        logs.append(f"Drive API: 파일 타입 '{mime_type}' 확인. 다운로드 요청 시작...")

        if mime_type == "application/vnd.google-apps.spreadsheet":
            request = service.files().export_media(
                fileId=file_id,
                mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            request = service.files().get_media(fileId=file_id)

        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        buffer.seek(0)
        logs.append("Drive API: 파일 다운로드 성공. 데이터프레임으로 변환 중...")

        read_kwargs = {"engine": "openpyxl"}
        if worksheet is not None:
            read_kwargs["sheet_name"] = worksheet
        df = pd.read_excel(buffer, **read_kwargs)
        logs.append("Drive API: 데이터프레임 변환 성공.")
        return df
    except HttpError as error:
        logs.append(f"Google Drive API 오류: {error}")
        return None
    except (OSError, ValueError) as error:
        logs.append(f"파일 처리 중 오류: {error}")
        return None


FOLDER_ID = "1F66ImTp4VxdPW2W-5jrGoJW1x72Y43Zy"


@st.cache_data(ttl=60)
def list_drive_photos(folder_id: str = FOLDER_ID):
    """Fetch photo metadata from Google Drive folder."""
    creds_info = load_service_account_info()
    if not creds_info:
        return []

    try:
        creds = service_account.Credentials.from_service_account_info(
            creds_info,
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
        service = build("drive", "v3", credentials=creds)
        response = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id, name)",
        ).execute()
        files = response.get("files", [])
    except Exception:
        return []

    results = []
    for file in files:
        file_id = file.get("id")
        name = file.get("name", "")
        if not file_id or not name:
            continue
        url = f"https://drive.google.com/uc?export=view&id={file_id}"
        results.append({"id": file_id, "name": name, "url": url})
    return results


@st.cache_data(ttl=60)
def build_photo_lookup():
    """Return mapping from photo key (file stem) to URL."""
    lookup = {}
    for item in list_drive_photos():
        stem = Path(item["name"]).stem.strip()
        if stem:
            lookup[stem] = item["url"]
    return lookup

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

# --- 데이터 로딩 ---
EXCEL_FILENAME = "조합장 현황.xlsx"

@st.cache_data(ttl=60)
def load_data():
    logs = []
    logs.append("데이터 로딩 시작")
    sheet_cfg = as_plain_dict(st.secrets.get('gsheets', {}))
    sheet_url = sheet_cfg.get('sheet_url')
    sheet_id = sheet_cfg.get('sheet_id') or sheet_cfg.get('spreadsheet_id')
    worksheet_name = sheet_cfg.get('worksheet', 'Sheet1')
    logs.append(f"Secrets에서 읽은 워크시트 이름: '{worksheet_name}'")
    df = None
    source = "알 수 없음"
    creds_info = load_service_account_info()

    # New Primary Method: Use Google Drive API to export the sheet as Excel, bypassing gspread
    if (sheet_url or sheet_id) and creds_info:
        logs.append("gspread를 우회하여 Google Drive API로 직접 다운로드를 시도합니다.")
        file_id = sheet_id
        if not file_id and sheet_url:
            match = re.search(r"/d/([^/]+)", sheet_url) or re.search(r"id=([^&]+)", sheet_url)
            if match:
                file_id = match.group(1)

        if file_id:
            downloaded = download_excel_from_drive(
                creds_info,
                file_id,
                logs,
                worksheet=worksheet_name,
            )
            if downloaded is not None and not downloaded.empty:
                df = downloaded
                source = "Google Drive (Sheet Export)"
                logs.append(f"Google Drive에서 {len(df)}행 로드 (시트: {worksheet_name or '기본'})")
            else:
                logs.append("Google Drive API를 통한 다운로드에 실패했습니다.")
        else:
            logs.append("secrets에서 Google Drive 파일 ID/URL을 찾을 수 없습니다.")

    # Fallback to local file
    if df is None or df.empty:
        logs.append(f"최종적으로 로컬 파일 '{EXCEL_FILENAME}'을 읽습니다.")
        try:
            df = pd.read_excel(EXCEL_FILENAME, engine='openpyxl')
            source = "로컬 파일"
            logs.append(f"로컬 파일 '{EXCEL_FILENAME}'에서 {len(df)}행 로드")
        except Exception as e:
            logs.append(f"로컬 파일 '{EXCEL_FILENAME}' 로딩 실패: {e}")
            st.error(f"모든 데이터 소스(Google, 로컬)에서 데이터를 불러오는 데 실패했습니다. 로컬 파일 '{EXCEL_FILENAME}'을 확인해주세요.")
            st.stop()

    if df is None:
        st.error("데이터프레임이 비어 있습니다. 데이터 소스를 확인해주세요.")
        st.stop()

    df = df.copy()
    required = ['성명', '농축협명']
    missing = [col for col in required if col not in df.columns]
    if missing:
        st.error(f"데이터에 필수 컬럼이 없습니다: {missing}. Google Sheet 또는 로컬 파일의 헤더를 확인해주세요.")
        st.stop()

    df['정제성명'] = df['성명'].astype(str).str.replace(' ', '').str.strip()
    df['정제농축협명'] = df['농축협명'].astype(str).str.replace(' ', '').str.strip()
    df['정제농축협명핵심'] = df['정제농축협명'].str.replace('농협', '', regex=False)
    logs.append("데이터 로딩 완료")
    return df, datetime.now(), source, logs

df, data_loaded_at, data_source, load_logs = load_data()

st.sidebar.caption(f"데이터 갱신: {data_loaded_at.strftime('%Y-%m-%d %H:%M:%S')}")
st.sidebar.caption(f"데이터 출처: {data_source}")
with st.sidebar.expander("로딩 로그", expanded=False):
    for entry in load_logs:
        st.write(f"- {entry}")

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
                    query_variants = {search_text}
                    shortened = search_text.replace('농협', '')
                    if shortened:
                        query_variants.add(shortened)
                    mask = pd.Series(False, index=df.index)
                    for token in query_variants:
                        if not token:
                            continue
                        mask |= df['정제농축협명'].str.contains(token, regex=False, na=False)
                        if '정제농축협명핵심' in df.columns:
                            mask |= df['정제농축협명핵심'].str.contains(token, regex=False, na=False)
                    results = df[mask]
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
            
            # --- 검색 결과 시각화 추가 ---
            if len(results) > 1:
                with st.expander("📊 검색 결과 시각화 분석", expanded=True):
                    st.markdown("###### 검색된 조합장들의 주요 분포")
                    
                    # 데이터 전처리 (시각화용)
                    viz_df = results.copy()
                    # 선수(당선횟수) 숫자 변환 시도
                    viz_df['선수_숫자'] = pd.to_numeric(viz_df['선수'], errors='coerce').fillna(0)
                    
                    col_viz1, col_viz2, col_viz3 = st.columns(3)
                    
                    with col_viz1:
                        # 유형별 분포 (파이차트 -> 도넛차트)
                        type_counts = viz_df['유형'].value_counts().reset_index()
                        type_counts.columns = ['유형', '인원수']
                        
                        base = alt.Chart(type_counts).encode(
                            theta=alt.Theta("인원수", stack=True)
                        )
                        pie = base.mark_arc(innerRadius=50).encode(
                            color=alt.Color("유형", legend=None),
                            order=alt.Order("인원수", sort="descending"),
                            tooltip=["유형", "인원수"]
                        )
                        text = base.mark_text(radius=140).encode(
                            text=alt.Text("인원수"),
                            order=alt.Order("인원수", sort="descending"),
                            color=alt.value("black")  # 다크모드 대응 필요시 조정
                        )
                        st.altair_chart(pie + text, use_container_width=True)
                        st.caption("유형별 분포")

                    with col_viz2:
                        # 선수별 분포 (막대)
                        term_counts = viz_df['선수'].value_counts().reset_index()
                        term_counts.columns = ['선수', '인원수']
                        
                        bar_term = alt.Chart(term_counts).mark_bar().encode(
                            x=alt.X('선수', sort='-y', title='당선 횟수'),
                            y=alt.Y('인원수', title='인원'),
                            color=alt.Color('선수', legend=None),
                            tooltip=['선수', '인원수']
                        ).properties(height=200)
                        st.altair_chart(bar_term, use_container_width=True)
                        st.caption("당선 횟수별 분포")

                    with col_viz3:
                        # 시도별 분포 (막대)
                        if '시도' in viz_df.columns:
                            region_counts = viz_df['시도'].value_counts().reset_index()
                            region_counts.columns = ['지역', '인원수']
                            
                            bar_region = alt.Chart(region_counts).mark_bar().encode(
                                x=alt.X('지역', sort='-y', title='지역'),
                                y=alt.Y('인원수', title='인원'),
                                color=alt.value('#3b82f6'),
                                tooltip=['지역', '인원수']
                            ).properties(height=200)
                            st.altair_chart(bar_region, use_container_width=True)
                            st.caption("지역별 분포")
            # ---------------------------
            photo_lookup = build_photo_lookup()
            for idx, row in results.iterrows():
                st.markdown(f"### 📋 [{row['성명']}] 조합장")
                tab1, tab2 = st.tabs(["상세 정보", "최신 뉴스"])
                with tab1:
                    candidates = []
                    photo_columns = ['순번', '사진번호', '사진ID', '사진키', '번호', 'No', 'no']
                    for col in photo_columns:
                        raw_value = row.get(col, '')
                        if pd.isna(raw_value):
                            continue
                        text_value = str(raw_value).strip()
                        if text_value.endswith('.0'):
                            text_value = text_value[:-2]
                        if text_value and text_value not in candidates:
                            candidates.append(text_value)
                    idx_candidate = ""
                    try:
                        idx_candidate = str(int(idx) + 1)
                    except (TypeError, ValueError, OverflowError):
                        idx_str = str(idx).strip()
                        if idx_str.isdigit():
                            idx_candidate = str(int(idx_str) + 1)
                    if idx_candidate and idx_candidate not in candidates:
                        candidates.append(idx_candidate)
                    name_value = str(row.get('성명', '')).strip()
                    if name_value and name_value not in candidates:
                        candidates.append(name_value)

                    photo_url = None
                    for key in candidates:
                        if key in photo_lookup:
                            photo_url = photo_lookup[key]
                            break

                    photo_key = next((candidate for candidate in candidates if candidate), None)
                    photo_path = f"photo/{photo_key}.jpg" if photo_key else None
                    if photo_url:
                        st.image(photo_url, caption=f"{row['성명']} 조합장 사진", width=180)
                    elif photo_path and os.path.exists(photo_path):
                        st.image(photo_path, caption=f"{row['성명']} 조합장 사진", width=180)
                    else:
                        st.info("📁 등록된 사진이 없습니다.")

                    info_data = []
                    printable_pairs = []
                    for col in df.columns:
                        if col in ['정제성명', '정제농축협명', '정제농축협명핵심']:
                            continue
                        value = row[col]
                        if col in ['출생년도', '출생연도']:
                            display_value = format_year_value(value)
                        elif col in ['임기시작일', '임기만료일']:
                            display_value = format_date_value(value)
                        else:
                            if pd.isnull(value):
                                display_value = "정보 없음"
                            else:
                                display_value = str(value).strip() or "정보 없음"
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
    st.title("📊 조합장 현황 종합 대시보드")
    st.write("전체 조합장 데이터에 대한 종합적인 통계와 분석 정보를 제공합니다.")

    # --- 데이터 전처리 ---
    analysis_df = df.copy()
    
    # 1. 나이 계산
    current_year = datetime.now().year
    if '출생연도' in analysis_df.columns:
        analysis_df['출생연도_숫자'] = pd.to_numeric(analysis_df['출생연도'], errors='coerce')
        analysis_df['나이'] = analysis_df['출생연도_숫자'].apply(lambda x: current_year - x if pd.notnull(x) else None)
        
        # 이상치 필터링 (나이가 0 이하이거나 120 이상인 경우 제외)
        # 예: 오기입된 데이터(19564년생 등)로 인한 평균 왜곡 방지
        analysis_df.loc[(analysis_df['나이'] <= 0) | (analysis_df['나이'] > 120), '나이'] = None
    else:
        analysis_df['나이'] = None
    
    # 2. 임기만료일 날짜 변환
    if '임기만료일' in analysis_df.columns:
        analysis_df['임기만료일_dt'] = pd.to_datetime(analysis_df['임기만료일'], errors='coerce')
        analysis_df['임기만료년도'] = analysis_df['임기만료일_dt'].dt.year
    else:
        analysis_df['임기만료일_dt'] = pd.NaT
        analysis_df['임기만료년도'] = None
    
    # 3. 선수 숫자 변환
    if '선수' in analysis_df.columns:
        analysis_df['선수_숫자'] = pd.to_numeric(analysis_df['선수'], errors='coerce')
    else:
        analysis_df['선수_숫자'] = None

    # --- KPI 지표 ---
    # 지표가 3개이므로 3열로 배치 (모바일에서는 자동 스택됨)
    kpi1, kpi2, kpi3 = st.columns(3)
    
    total_count = len(analysis_df)
    avg_age = analysis_df['나이'].mean() if '나이' in analysis_df.columns else None
    
    # 부가의결권 보유 수 계산
    vote_count_kpi = 0
    if '부가의결권' in analysis_df.columns:
        vote_count_kpi = len(analysis_df[analysis_df['부가의결권'].astype(str).str.strip() == '여'])

    with kpi1:
        st.metric("전체 조합장 수", f"{total_count}명")
    with kpi2:
        st.metric("평균 연령", f"{avg_age:.1f}세" if pd.notnull(avg_age) else "-")
    with kpi3:
        st.metric("부가의결권 보유", f"{vote_count_kpi}개소", delta_color="off")

    st.divider()

    # --- 탭 구성 ---
    tab1, tab2, tab3 = st.tabs(["📈 인구/유형 분석", "🗺️ 지역별 분석", "�️ 부가의결권 분석"])

    with tab1:
        # 모바일 가독성을 위해 컬럼 분할 제거하고 순차 배치
        st.subheader("연령대별 분포")
        if '나이' in analysis_df.columns:
            # 연령대 구간 생성
            analysis_df['연령대'] = (analysis_df['나이'] // 10 * 10).fillna(-1).astype(int).astype(str) + "대"
            analysis_df.loc[analysis_df['연령대'] == "-1대", '연령대'] = "정보없음"
            
            age_counts = analysis_df['연령대'].value_counts().reset_index()
            age_counts.columns = ['연령대', '인원수']
            # 정렬
            age_counts = age_counts.sort_values('연령대')
            
            chart_age = alt.Chart(age_counts).mark_bar().encode(
                x=alt.X('연령대', title='연령대'),
                y=alt.Y('인원수', title='인원(명)'),
                color=alt.value('#f59e0b'),
                tooltip=['연령대', '인원수']
            ).properties(height=300)
            st.altair_chart(chart_age, use_container_width=True)
    
        st.divider()

        st.subheader("당선 횟수(선수) 분포")
        term_counts = analysis_df['선수'].value_counts().reset_index()
        term_counts.columns = ['선수', '인원수']
        
        chart_term = alt.Chart(term_counts).mark_bar().encode(
            x=alt.X('선수', sort='-y', title='당선 횟수'),
            y=alt.Y('인원수', title='인원(명)'),
            color=alt.value('#10b981'),
            tooltip=['선수', '인원수']
        ).properties(height=300)
        st.altair_chart(chart_term, use_container_width=True)

        st.subheader("유형별 구성 비율")
        type_counts = analysis_df['유형'].value_counts().reset_index()
        type_counts.columns = ['유형', '인원수']
        
        chart_type = alt.Chart(type_counts).mark_arc(innerRadius=60).encode(
            theta=alt.Theta("인원수", stack=True),
            color=alt.Color("유형", legend=alt.Legend(title="유형")),
            tooltip=["유형", "인원수"],
            order=alt.Order("인원수", sort="descending")
        ).properties(height=300)
        
        st.altair_chart(chart_type, use_container_width=True)

    with tab2:
        st.subheader("지역별 조합장 현황")
        if '시도' in analysis_df.columns:
            region_counts = analysis_df['시도'].value_counts().reset_index()
            region_counts.columns = ['지역', '인원수']
            
            chart_region = alt.Chart(region_counts).mark_bar().encode(
                x=alt.X('지역', sort='-y', title='지역'),
                y=alt.Y('인원수', title='인원(명)'),
                color=alt.Color('지역', legend=None, scale=alt.Scale(scheme='category20')),
                tooltip=['지역', '인원수']
            ).properties(height=400)
            st.altair_chart(chart_region, use_container_width=True)
            
            with st.expander("지역별 상세 데이터 보기"):
                st.dataframe(region_counts)

    with tab3:
        st.subheader("🗳️ 부가의결권 보유 현황")
        if '부가의결권' in analysis_df.columns:
            # 부가의결권 값이 '여'인 데이터 필터링 (공백 제거 등 전처리)
            vote_df = analysis_df[analysis_df['부가의결권'].astype(str).str.strip() == '여']
            vote_count = len(vote_df)
            vote_ratio = (vote_count / total_count * 100) if total_count > 0 else 0
            
            # 요약 메트릭
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                st.metric("부가의결권 보유 조합 수", f"{vote_count}개")
            with col_v2:
                st.metric("전체 대비 비율", f"{vote_ratio:.1f}%")
            
            st.divider()
            
            st.divider()
            
            # 시각화: 지역별 분포 (모바일 최적화를 위해 순차 배치)
            st.markdown("###### 지역별 부가의결권 보유 분포")
            if '시도' in vote_df.columns:
                vote_region_counts = vote_df['시도'].value_counts().reset_index()
                vote_region_counts.columns = ['지역', '보유수']
                
                chart_vote_region = alt.Chart(vote_region_counts).mark_bar().encode(
                    x=alt.X('지역', sort='-y', title='지역'),
                    y=alt.Y('보유수', title='조합 수'),
                    color=alt.value('#8b5cf6'),
                    tooltip=['지역', '보유수']
                ).properties(height=300)
                st.altair_chart(chart_vote_region, use_container_width=True)

            st.divider()

            st.markdown("###### 유형별 부가의결권 보유 분포")
            if '유형' in vote_df.columns:
                vote_type_counts = vote_df['유형'].value_counts().reset_index()
                vote_type_counts.columns = ['유형', '보유수']
                
                chart_vote_type = alt.Chart(vote_type_counts).mark_arc(innerRadius=40).encode(
                    theta=alt.Theta("보유수", stack=True),
                    color=alt.Color("유형", legend=alt.Legend(title="유형"), scale=alt.Scale(scheme='pastel1')),
                    tooltip=["유형", "보유수"],
                    order=alt.Order("보유수", sort="descending")
                ).properties(height=300)
                st.altair_chart(chart_vote_type, use_container_width=True)
            
            st.markdown("###### 부가의결권 보유 조합 목록")
            with st.expander("목록 보기 (클릭)", expanded=True):
                display_cols = [c for c in ['농축협명', '성명', '시도', '시군', '유형'] if c in vote_df.columns]
                st.dataframe(vote_df[display_cols].reset_index(drop=True))
        else:
            st.warning("데이터에 '부가의결권' 컬럼이 존재하지 않습니다.")

    # --- 상세 데이터 탐색 (기존 기능 유지 및 개선) ---
    st.divider()
    st.subheader("🔎 상세 데이터 탐색")
    st.write("원하는 컬럼을 선택하여 세부 분포를 확인할 수 있습니다.")
    
    exclude_cols = [
        '정제성명', '정제농축협명', '정제농축협명핵심', '사진ID', '사진키', '사진번호',
        '순번', '시도', '성명', '주요경력', '임기시작일', '임기만료일', '부가의결권', '비고', '연락처'
    ]
    columns = [col for col in df.columns if col not in exclude_cols]
    
    default_idx = columns.index('시군') if '시군' in columns else 0
    selected_column = st.selectbox("분석할 컬럼 선택", columns, index=default_idx)
    
    if selected_column:
        val_counts = df[selected_column].value_counts().reset_index()
        val_counts.columns = [selected_column, '건수']
        st.bar_chart(val_counts.set_index(selected_column))
        with st.expander("데이터 표 보기"):
            st.dataframe(val_counts)


# --- 사이드바 및 메인 로직 ---



# --- 사이드바 및 메인 로직 ---
st.sidebar.title("메뉴")
menu_options = ("조합장 정보 검색", "통계 자료")
menu = st.sidebar.radio("원하는 작업을 선택하세요", menu_options)

if menu == "조합장 정보 검색":
    show_search_page(df)
else:
    show_analysis_page(df)


