import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime

# ==========================================
# 1. 페이지 및 기본 설정
# ==========================================
st.set_page_config(page_title="특성화고 스펙 관리 시스템", page_icon="🎓", layout="wide")

# ==========================================
# 2. Supabase 데이터베이스 연결
# ==========================================
@st.cache_resource
def init_connection() -> Client:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"데이터베이스 연결 설정에 실패했습니다: {e}")
        st.stop()

supabase = init_connection()

# ==========================================
# 3. 세션 상태(Session State) 초기화
# ==========================================
# role: None (초기화면), 'student' (학생), 'teacher' (교사)
if 'role' not in st.session_state:
    st.session_state.role = None
if 'student_logged_in' not in st.session_state:
    st.session_state.student_logged_in = False
if 'student_info' not in st.session_state:
    st.session_state.student_info = None
if 'teacher_logged_in' not in st.session_state:
    st.session_state.teacher_logged_in = False

# 공통 로그아웃/초기화면 복귀 함수
def reset_to_home():
    st.session_state.role = None
    st.session_state.student_logged_in = False
    st.session_state.student_info = None
    st.session_state.teacher_logged_in = False

# ==========================================
# 4. 화면 라우팅 - [A] 초기 역할 선택 화면
# ==========================================
if st.session_state.role is None:
    st.markdown("<h1 style='text-align: center; margin-top: 50px;'>🎓 특성화고 스펙 관리 시스템</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>자신의 역할에 맞게 로그인해 주세요.</p>", unsafe_allow_html=True)
    
    st.write("")
    st.write("")
    
    col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
    
    with col2:
        st.info("👨‍🎓 **학생용**\n\n내신, 자격증, 자기소개서 등 본인의 스펙을 직접 관리하고 확인합니다.")
        if st.button("학생용으로 접속하기", use_container_width=True, type="primary"):
            st.session_state.role = 'student'
            st.rerun()
            
    with col3:
        st.success("👨‍🏫 **교사용**\n\n전체 학생의 스펙 현황을 한눈에 조회하고 관리합니다.")
        if st.button("교사용으로 접속하기", use_container_width=True, type="primary"):
            st.session_state.role = 'teacher'
            st.rerun()

# ==========================================
# 5. 화면 라우팅 - [B] 교사용 관리 페이지
# ==========================================
elif st.session_state.role == 'teacher':
    with st.sidebar:
        st.title("👨‍🏫 교사용 관리자")
        if st.button("⬅️ 초기 화면으로", use_container_width=True):
            reset_to_home()
            st.rerun()
            
        if st.session_state.teacher_logged_in:
            st.divider()
            if st.button("로그아웃", use_container_width=True):
                st.session_state.teacher_logged_in = False
                st.rerun()

    if not st.session_state.teacher_logged_in:
        st.subheader("🔐 관리자 인증")
        admin_pw = st.text_input("교사용 비밀번호를 입력하세요", type="password")
        if st.button("인증하기"):
            if admin_pw == st.secrets.get("ADMIN_PASSWORD", "admin"):
                st.session_state.teacher_logged_in = True
                st.rerun()
            else:
                st.error("비밀번호가 일치하지 않습니다.")
    else:
        st.title("📊 전체 학생 스펙 관리 대시보드")
        
        try:
            # 학생 데이터와 스펙 데이터 모두 가져오기
            students_res = supabase.table("students").select("*").execute()
            specs_res = supabase.table("specs").select("*").execute()
            
            df_students = pd.DataFrame(students_res.data)
            df_specs = pd.DataFrame(specs_res.data)
            
            if not df_students.empty:
                # 데이터 병합 (Left Join)
                if not df_specs.empty:
                    df_merged = pd.merge(df_students, df_specs, left_on='id', right_on='student_id', how='left')
                else:
                    df_merged = df_students.copy()
                    df_merged['gpa'] = None
                    df_merged['certificates'] = ""
                    df_merged['cover_letter'] = ""
                
                # 교사가 보기 편하도록 데이터 가공
                df_merged['gpa'] = df_merged['gpa'].fillna(0.0)
                df_merged['cert_count'] = df_merged['certificates'].apply(lambda x: len([c for c in str(x).split('\n') if c.strip()]) if pd.notnull(x) and x else 0)
                df_merged['cl_status'] = df_merged['cover_letter'].apply(lambda x: "작성 완료" if pd.notnull(x) and len(str(x).strip()) > 10 else "미작성")
                
                # 필요한 컬럼만 추출 및 이름 변경
                display_df = df_merged[['student_number', 'name', 'major', 'gpa', 'cert_count', 'cl_status']].copy()
                display_df.columns = ['학번', '이름', '전공', '내신 등급', '자격증 개수', '자소서 상태']
                display_df = display_df.sort_values(by='학번').reset_index(drop=True)
                
                # 검색 및 필터링 기능
                st.subheader("🔍 학생 검색")
                col1, col2 = st.columns(2)
                with col1:
                    search_query = st.text_input("학번 또는 이름으로 검색")
                with col2:
                    major_filter = st.selectbox("전공 필터", ["전체"] + list(display_df['전공'].unique()))
                
                # 필터 적용
                if search_query:
                    display_df = display_df[display_df['학번'].astype(str).str.contains(search_query) | display_df['이름'].str.contains(search_query)]
                if major_filter != "전체":
                    display_df = display_df[display_df['전공'] == major_filter]
                
                st.write(f"**총 {len(display_df)} 명의 학생이 조회되었습니다.**")
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                
            else:
                st.info("등록된 학생 데이터가 없습니다.")
                
        except Exception as e:
            st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")

# ==========================================
# 6. 화면 라우팅 - [C] 학생용 스펙 관리 페이지
# ==========================================
elif st.session_state.role == 'student':
    with st.sidebar:
        st.title("👨‍🎓 학생용 시스템")
        if st.button("⬅️ 초기 화면으로", use_container_width=True):
            reset_to_home()
            st.rerun()
        st.divider()
        
        if not st.session_state.student_logged_in:
            st.header("🔐 학생 로그인")
            with st.form("login_form"):
                student_num = st.text_input("학번 (숫자만 입력)", max_chars=10)
                student_name = st.text_input("이름")
                major = st.selectbox("전공/학과", ["기계과", "전자과", "전기과", "소프트웨어과", "디자인과", "경영과", "기타"])
                submit_btn = st.form_submit_button("시작하기")
                
                if submit_btn:
                    if student_num and student_name and student_num.isdigit():
                        try:
                            # 학번으로 DB 검색 후 이름 비교 (인코딩 에러 방지)
                            response = supabase.table("students").select("*").eq("student_number", student_num).execute()
                            
                            if len(response.data) > 0:
                                if response.data[0]['name'] == student_name:
                                    st.session_state.student_info = response.data[0]
                                    st.session_state.student_logged_in = True
                                    st.rerun()
                                else:
                                    st.warning("학번과 이름이 일치하지 않습니다.")
                            else:
                                # 신규 가입
                                new_student = {"student_number": student_num, "name": student_name, "major": major}
                                insert_res = supabase.table("students").insert(new_student).execute()
                                st.session_state.student_info = insert_res.data[0]
                                st.session_state.student_logged_in = True
                                st.rerun()
                        except Exception as e:
                            st.error(f"로그인 오류: {e}")
                    else:
                        st.warning("학번(숫자)과 이름을 정확히 입력해주세요.")
        else:
            st.success(f"👤 {st.session_state.student_info['name']} 학생")
            if st.button("로그아웃", use_container_width=True):
                st.session_state.student_logged_in = False
                st.session_state.student_info = None
                st.rerun()
                
            st.divider()
            menu = st.radio("메뉴 이동", ["대시보드", "스펙 관리", "자기소개서 뷰어"])

    # 학생용 메인 화면
    if not st.session_state.student_logged_in:
        st.title("👋 환영합니다, 학생 여러분!")
        st.write("왼쪽 사이드바에서 학번과 이름을 입력하여 본인의 스펙 관리를 시작하세요.")
    else:
        student_id = st.session_state.student_info['id']
        
        # 스펙 데이터 로드
        specs_data = None
        try:
            res = supabase.table("specs").select("*").eq("student_id", student_id).execute()
            if len(res.data) > 0:
                specs_data = res.data[0]
        except:
            pass
        
        current_gpa = specs_data['gpa'] if specs_data and specs_data.get('gpa') else 0.0
        current_certs = specs_data['certificates'] if specs_data and specs_data.get('certificates') else ""
        current_cover_letter = specs_data['cover_letter'] if specs_data and specs_data.get('cover_letter') else ""

        if menu == "대시보드":
            st.title("📊 나의 스펙 요약")
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("📈 내신 등급", f"{current_gpa} 등급")
            with col2: st.metric("🏆 자격증", f"{len([c for c in current_certs.split() if c])} 개")
            with col3: st.metric("📝 자소서", f"{len(current_cover_letter.replace(' ', ''))} 자")

        elif menu == "스펙 관리":
            st.title("🛠️ 스펙 입력 및 수정")
            with st.form("specs_form"):
                new_gpa = st.number_input("내신 등급", value=float(current_gpa), step=0.1)
                new_certs = st.text_area("자격증 목록 (엔터로 구분)", value=current_certs, height=100)
                new_cl = st.text_area("자기소개서", value=current_cover_letter, height=300)
                
                if st.form_submit_button("저장하기"):
                    save_payload = {
                        "student_id": student_id, "gpa": new_gpa, 
                        "certificates": new_certs, "cover_letter": new_cl,
                        "updated_at": datetime.utcnow().isoformat()
                    }
                    try:
                        if specs_data:
                            supabase.table("specs").update(save_payload).eq("id", specs_data['id']).execute()
                        else:
                            supabase.table("specs").insert(save_payload).execute()
                        st.success("🎉 성공적으로 저장되었습니다!")
                        st.balloons()
                    except Exception as e:
                        st.error("저장 실패")

        elif menu == "자기소개서 뷰어":
            st.title("📄 자기소개서 뷰어")
            if current_cover_letter:
                st.code(current_cover_letter, language="markdown")
                st.markdown(current_cover_letter)
            else:
                st.warning("작성된 내용이 없습니다.")
