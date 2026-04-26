import streamlit as st
import requests
from datetime import datetime

# ==========================================
# 1. 페이지 및 기본 설정
# ==========================================
st.set_page_config(page_title="특성화고 스펙 관리 대시보드", page_icon="🎓", layout="wide")

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except KeyError:
    st.error("🚨 .streamlit/secrets.toml 파일에 SUPABASE_URL 또는 SUPABASE_KEY가 없습니다.")
    st.stop()

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'student_info' not in st.session_state:
    st.session_state.student_info = None

# ==========================================
# 2. 사이드바 - 로그인 및 메뉴
# ==========================================
with st.sidebar:
    st.title("🎓 스펙 관리 시스템")

    if not st.session_state.logged_in:
        st.header("🔐 로그인 / 등록")

        with st.form("login_form"):
            student_num = st.text_input("학번 (숫자만 입력)", max_chars=10)
            student_name = st.text_input("이름")
            major = st.selectbox("전공/학과", ["항공정비과", "항공기계과", "항공전기전자과"])
            submit_btn = st.form_submit_button("시작하기")

            if submit_btn:
                if student_num and student_name:
                    if not student_num.isdigit():
                        st.warning("⚠️ 학번은 숫자만 입력해주세요.")
                    else:
                        # 💡 통신 상태를 꼼꼼히 체크하는 로직으로 강화
                        search_url = f"{SUPABASE_URL}/rest/v1/students?student_number=eq.{student_num}"
                        res = requests.get(search_url, headers=HEADERS)

                        if not res.ok:  # 에러가 발생했다면 진짜 이유를 화면에 출력!
                            st.error(f"DB 통신 거절: {res.text}")
                        else:
                            students_data = res.json()

                            if len(students_data) > 0:
                                if students_data[0]['name'] == student_name:
                                    st.session_state.student_info = students_data[0]
                                    st.session_state.logged_in = True
                                    st.success(f"환영합니다, {student_name}님!")
                                    st.rerun()
                                else:
                                    st.warning("학번과 이름이 일치하지 않습니다.")
                            else:
                                insert_url = f"{SUPABASE_URL}/rest/v1/students"
                                payload = {"student_number": student_num, "name": student_name, "major": major}
                                insert_res = requests.post(insert_url, headers=HEADERS, json=payload)

                                if not insert_res.ok:
                                    st.error(f"학생 등록 실패: {insert_res.text}")
                                else:
                                    st.session_state.student_info = insert_res.json()[0]
                                    st.session_state.logged_in = True
                                    st.success(f"환영합니다, {student_name}님!")
                                    st.rerun()
                else:
                    st.warning("학번과 이름을 모두 입력해주세요.")
    else:
        st.success(f"👤 {st.session_state.student_info['name']} 로그인됨")
        if st.button("로그아웃"):
            st.session_state.logged_in = False
            st.session_state.student_info = None
            st.rerun()

        st.divider()
        st.header("📌 메뉴")
        menu = st.radio("이동할 페이지:", ["대시보드", "스펙 관리", "자기소개서 뷰어"])

# ==========================================
# 3. 메인 화면 로직
# ==========================================
if not st.session_state.logged_in:
    st.title("👋 환영합니다!")
    st.write("왼쪽 사이드바에서 학번과 이름을 입력하여 시작하세요.")
else:
    student_id = st.session_state.student_info['id']

    specs_data = None
    spec_url = f"{SUPABASE_URL}/rest/v1/specs?student_id=eq.{student_id}"
    spec_res = requests.get(spec_url, headers=HEADERS)

    if spec_res.ok:
        specs_list = spec_res.json()
        if len(specs_list) > 0:
            specs_data = specs_list[0]

    current_gpa = specs_data['gpa'] if specs_data and specs_data.get('gpa') else 0.0
    current_certs = specs_data['certificates'] if specs_data and specs_data.get('certificates') else ""
    current_cover_letter = specs_data['cover_letter'] if specs_data and specs_data.get('cover_letter') else ""

    if menu == "대시보드":
        st.title("📊 나의 스펙 요약 대시보드")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📈 내신 등급", f"{current_gpa} 등급")
        with col2:
            st.metric("🏆 자격증", f"{len([c for c in current_certs.split() if c])} 개")
        with col3:
            st.metric("📝 자소서", f"{len(current_cover_letter.replace(' ', ''))} 자")

    elif menu == "스펙 관리":
        st.title("🛠️ 스펙 입력 및 수정")
        with st.form("specs_form"):
            new_gpa = st.number_input("내신 등급", value=float(current_gpa), step=0.1)
            new_certs = st.text_area("자격증 목록 (엔터로 구분)", value=current_certs, height=100)
            new_cl = st.text_area("자기소개서", value=current_cover_letter, height=300)

            if st.form_submit_button("저장하기"):
                save_payload = {
                    "student_id": student_id,
                    "gpa": new_gpa,
                    "certificates": new_certs,
                    "cover_letter": new_cl,
                    "updated_at": datetime.utcnow().isoformat()
                }

                if specs_data:
                    update_url = f"{SUPABASE_URL}/rest/v1/specs?id=eq.{specs_data['id']}"
                    res = requests.patch(update_url, headers=HEADERS, json=save_payload)
                else:
                    insert_spec_url = f"{SUPABASE_URL}/rest/v1/specs"
                    res = requests.post(insert_spec_url, headers=HEADERS, json=save_payload)

                if not res.ok:
                    st.error(f"저장 실패: {res.text}")
                else:
                    st.success("🎉 데이터가 성공적으로 저장되었습니다!")
                    st.balloons()

    elif menu == "자기소개서 뷰어":
        st.title("📄 자기소개서 뷰어")
        if current_cover_letter:
            st.code(current_cover_letter, language="markdown")
            st.markdown(current_cover_letter)
        else:
            st.warning("작성된 내용이 없습니다.")