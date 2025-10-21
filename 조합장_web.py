import streamlit as st
import pandas as pd
import os
from datetime import datetime
from urllib.parse import quote

# 페이지 설정
st.set_page_config(page_title="조합장 검색기", layout="centered")

st.title("🧑‍🌾 조합장 정보 검색기")
st.write("검색 기준을 선택한 뒤 성명 또는 농축협명으로 조합장 정보를 조회할 수 있습니다.")

# ✅ 엑셀 파일명
EXCEL_FILENAME = "조합장현황.xlsx"

# ✅ 데이터 로딩
@st.cache_data
def load_data():
    return pd.read_excel(EXCEL_FILENAME, engine='openpyxl')

df = load_data()

# ✅ 정제 열 추가
df['정제성명'] = df['성명'].astype(str).str.replace(' ', '').str.strip()
df['정제농축협명'] = df['농축협명'].astype(str).str.replace(' ', '').str.strip()

# --- 상태 관리 --- #
if 'results' not in st.session_state:
    st.session_state.results = None
if 'query' not in st.session_state:
    st.session_state.query = ""
# --- 상태 관리 끝 --- #

# ✅ 검색 UI
search_option = st.radio("검색 기준 선택", ["성명", "농축협명"], horizontal=True)
# text_input의 기본값을 session_state.query로 설정하여 검색어 유지
query = st.text_input(f"🔍 {search_option} 입력", st.session_state.query)

col1, col2 = st.columns([3, 1])
with col1:
    if st.button("검색하기"):
        if query:
            # 새로운 검색이 수행되면 상태 업데이트
            search_text = query.replace('\n', '').replace('\r', '').replace(' ', '').strip()
            if search_option == "성명":
                results = df[df['정제성명'] == search_text]
            else:
                results = df[df['정제농축협명'].str.contains(f'^{search_text}$', regex=True)]
            st.session_state.results = results
            st.session_state.query = query
        else:
            # 검색어가 없을 경우 결과 초기화
            st.session_state.results = None
            st.session_state.query = ""
        st.rerun()

with col2:
    if st.button("초기화"):
        st.session_state.results = None
        st.session_state.query = ""
        st.rerun()

# ✅ 검색 결과 표시 (세션 상태에서 결과 가져오기)
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
                # 사진 표시
                photo_path = f"photo/{row['순번']}.jpg"
                if os.path.exists(photo_path):
                    st.image(photo_path, caption=f"{row['성명']} 조합장 사진", width=300)
                else:
                    st.info("📁 등록된 사진이 없습니다.")
                    st.text(f"(경로 확인용: {photo_path})")

                # 정보 테이블 표시
                info_data = []
                for col in df.columns:
                    if col in ['정제성명', '정제농축협명']:
                        continue
                    value = row[col]

                    # 출생연도 처리
                    if col == '출생연도' and pd.notna(value):
                        try:
                            value = int(float(value))
                        except (ValueError, TypeError):
                            pass # 변환 실패 시 원본 값 유지

                    if col in ['임기시작일', '임기만료일']:
                        v = None
                        num = pd.to_numeric(str(value).strip(), errors='coerce')
                        if pd.notna(num):
                            v = pd.to_datetime(num, origin='1899-12-30', unit='D', errors='coerce')
                        else:
                            v = pd.to_datetime(value, errors='coerce')
                        if pd.notna(v):
                            value = v.strftime('%Y-%m-%d')
                    if pd.isnull(value):
                        value = "정보 없음"
                    info_data.append([col, value])
                info_df = pd.DataFrame(info_data, columns=["항목", "내용"])
                info_df['내용'] = info_df['내용'].astype(str)
                st.table(info_df.set_index("항목"))

            with tab2:
                search_query = f"{row['농축협명']} {row['성명']}"
                encoded_query = quote(search_query)
                
                st.write(f"아래 링크를 클릭하면 '{search_query}'에 대한 뉴스 검색 결과가 새 탭에서 열립니다.")
                st.divider()

                # 1. Google News
                google_url = f"https://news.google.com/search?q={encoded_query}"
                st.markdown(f"### 📰 [Google 뉴스 검색]({google_url})")

                # 2. Naver News
                naver_url = f"https://search.naver.com/search.naver?where=news&query={encoded_query}"
                st.markdown(f"### 📰 [네이버 뉴스 검색]({naver_url})")

                # 3. Daum News
                daum_url = f"https://search.daum.net/search?w=news&q={encoded_query}"
                st.markdown(f"### 📰 [다음 뉴스 검색]({daum_url})")

            st.markdown("-----")
