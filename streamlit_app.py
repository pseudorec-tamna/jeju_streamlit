import os
import streamlit as st
from PIL import Image
from io import BytesIO
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from utils.prepare import (
    get_logger,
    GEMINI_API_KEY
)
from utils.query_parsing import parse_query
from components.llm import CallbackHandlerDDGStreamlit
from agents.final_pretty import df_filter, display_store_info
from utils.chat_state import ChatState
from utils.streamlit.prepare import prepare_app
from utils.helpers import (
    DELIMITER,
    GREETING_MESSAGE_KOR,
    GREETING_MESSAGE_ENG,
    VERSION,
    WALKTHROUGH_TEXT,
)
from agents.dbmanager import (
    get_user_facing_collection_name,
)
from utils.type_utils import (
    ChatMode
)
from utils.lang_utils import pairwise_chat_history_to_msg_list
from utils.streamlit.helpers import (
    mode_options,
    age_options,
    STAND_BY_FOR_INGESTION_MESSAGE,
    status_config,
    show_sources,
    show_downloader,
    fix_markdown,    
    show_uploader,
    just_chat_status_config,
)
from streamlit_modal import Modal
from tamla import get_bot_response

# 로그 설정 
logger = get_logger()

# Show title and description.
st.logo(logo := "media/탐라logo_wo_words.png")
st.set_page_config(page_title="Tamla's Flavor", page_icon=logo)

# HTML and CSS for the logo size customization.
st.markdown("""
    <style>
        [alt=Logo] {
            height: 3rem;
        }
        code {
            color: #005F26;
            overflow-wrap: break-word;
            font-weight: 600;
        }
        [data-testid=stSidebar] {
        background-color: #ffe5be;
        }   
        .stButton > button {
        width: 100%;
        border-radius: 20px;
        font-weight: bold;
        }
        .stButton > button:hover {
            background-color: #f0f0f0;
            color: #4F8BF9;
        }
    </style>
    """, unsafe_allow_html=True) # text color for dark theme: e6e6e6

# seesion management (api key, query parameters, ...)
ss = st.session_state
if "chat_state" not in ss:
    # Run just once
    prepare_app()
    # Need to reference is_env_loaded to avoid unused import being removed
    is_env_loaded = True  # more info at the end of docdocgo.py

chat_state: ChatState = ss.chat_state

def open_ai_chat(eng_flag=False):
    # 채팅창 생성
    if "messages" not in ss:
        ss.messages = []

    # 기존 메시지 표시
    for message in ss.messages:
        with st.chat_message(message["role"], avatar=message.get("avatar")):
            st.markdown(message["content"])

    # 질문지 생성 
    with st.container():
        clicked_sample_query = questions_recommending()

    # Chat 입력창 설명 
    if eng_flag:
        temp_prompt = st.chat_input("How can I assist you?")
    elif clicked_sample_query:
        temp_prompt = clicked_sample_query
    else:
        temp_prompt = st.chat_input("무엇을 도와드릴까요?")

    if prompt := temp_prompt:
        # Parse the query or get the next scheduled query, if any
        parsed_query = parse_query(prompt, predetermined_chat_mode=ChatMode.CHAT_HW_ID)
        chat_state.update(parsed_query=parsed_query)

        ss.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=ss.user_avatar):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar=ss.bot_avatar):
            try:
                chat_mode = parsed_query.chat_mode
                status = st.status(status_config[chat_mode]["thinking.header"])
                status.write(status_config[chat_mode]["thinking.body"])
            except KeyError:
                status = None

            # Prepare container and callback handler for showing streaming response
            message_placeholder = st.empty()

            cb = CallbackHandlerDDGStreamlit(
                message_placeholder,
                end_str=STAND_BY_FOR_INGESTION_MESSAGE
            )
            chat_state.callbacks[1] = cb
            chat_state.add_to_output = lambda x: cb.on_llm_new_token(x, run_id=None)                

            response = get_bot_response(chat_state)
            answer = response["answer"]

            # Display the "complete" status - custom or default
            if status:
                default_status = status_config.get(chat_mode, just_chat_status_config)
                status.update(
                    label=response.get("status.header", default_status["complete.header"]),
                    state="complete",
                )
                status.write(response.get("status.body", default_status["complete.body"]))

            # Add the response to the chat history
            chat_state.chat_history.append((prompt, answer))
            # chat_state.memory.load_memory_variables({})["chat_history"] = pairwise_chat_history_to_msg_list(chat_state.chat_history)
            message_placeholder.markdown(fix_markdown(answer))
        ss.messages.append({"role": "assistant", "content": answer})
        # 페이지 새로고침
        st.rerun()
    # else:
    #     st.info("OpenAI API 키를 입력해주세요.", icon="🗝️")

def user_id_setting(): 
    user_id = st.sidebar.text_input("User ID", 
                                    label_visibility='visible',
                                    disabled=False,
                                    placeholder="홍길동")
    # 양쪽 공백 제거
    user_id = user_id.strip()

    # Check if the user ID has changed
    if user_id != chat_state.user_id:
        if user_id == "":
            chat_state.user_id = None
        else:
            # Update user_id in chat_state
            chat_state.user_id = user_id

            # Append chat history when user_id changes
            chat_state.chat_history.append(
                ("", "앞으로 내 이름을 언급하면서, 친절하게 답변해줘. 내 이름은 " + chat_state.user_id + ".")
            )
            chat_state.chat_history_all.append(
                ("", "앞으로 내 이름을 언급하면서, 친절하게 답변해줘. 내 이름은 " + chat_state.user_id + ".")
            )

def age():
    # 세션 상태 초기화
    # if 'selected_age_groups' not in chat_state:
    # chat_state.selected_age_groups = [list(age_options.keys())[1]]

    # Default mode
    with st.expander("나이대 선택", expanded=True):
        selected_age_groups = st.multiselect(
            "나이대 복수 선택 가능", # 더 맞춤형 서비스를 제공해드리겠습니다. 
            options=list(age_options.keys()),
            default=[],
            key="age_multiselect"
        )
        
        # 선택된 나이대 저장
        chat_state.selected_age_groups = selected_age_groups
        
        if selected_age_groups:
            cmd_prefixes = []
            cmd_prefix_explainers = []
            for age_group in selected_age_groups:
                cmd_prefix, cmd_prefix_explainer, _ = age_options[age_group]
                cmd_prefixes.append(cmd_prefix)
                cmd_prefix_explainers.append(cmd_prefix_explainer)
            
            st.caption("선택된 나이대:")
            for age_group, explainer in zip(selected_age_groups, cmd_prefix_explainers):
                st.caption(f"• {age_group}: {explainer}")
        else:
            st.caption("나이대를 선택해주세요.")

    # 선택된 나이대 확인 (디버깅용)
    # st.write("현재 선택된 나이대:", chat_state.selected_age_groups)

def gender():
    # 세션 상태 초기화
    # if 'gender' not in chat_state:
        # chat_state.gender = None

    # 사이드바에 성별 선택 버튼 추가
    with st.expander("성별 선택", expanded=True):
        # st.write("## 성별 선택")
        col1, col2 = st.columns(2)
        
        # 남성 버튼
        if col1.button("남성", key="male", 
                    use_container_width=True,
                    type="primary" if chat_state.gender == "남성" else "secondary"):
            if chat_state.gender == "남성":
                chat_state.gender = None  # 이미 선택된 경우 취소
            else:
                chat_state.gender = "남성"
        
        # 여성 버튼
        if col2.button("여성", key="female", 
                    use_container_width=True,
                    type="primary" if chat_state.gender == "여성" else "secondary"):
            if chat_state.gender == "여성":
                chat_state.gender = None  # 이미 선택된 경우 취소
            else:
                chat_state.gender = "여성"

def car():
    # 사이드바에 주차 선택 버튼 추가
    with st.expander("주차 유무 선택", expanded=True):
        # st.write("## 성별 선택")
        col1, col2 = st.columns(2)
        
        # 유 버튼
        if col1.button("유", key="y", 
                    use_container_width=True,
                    type="primary" if chat_state.car == "y" else "secondary"):
            chat_state.car = "y"

        # 무 버튼
        if col2.button("무", key="n", 
                    use_container_width=True,
                    type="primary" if chat_state.car == "n" else "secondary"):
            chat_state.car = "n"


def food_selection():
    # 음식 종류 리스트
    food_types = ["한식", "일식", "중식", "양식", "멕시코 음식", "기타"]

    # 세션 상태 초기화
    # if 'selected_foods' not in chat_state:
    #     chat_state.selected_foods = []

    with st.expander("음식 종류 선택", expanded=True):
        st.write("어떤 음식을 드시고 싶으신가요? (복수 선택 가능)")
        
        selected_foods = []
        for food in food_types:
            if st.checkbox(food, key=f"food_{food}"):
                selected_foods.append(food)
        chat_state.selected_foods = selected_foods

        # if chat_state.selected_foods:
        #     st.write("선택된 음식 종류:")
        #     st.write(", ".join(chat_state.selected_foods))
        # else:
        #     st.write("아직 선택된 음식이 없습니다.")

def price():
    # Settings
    with st.expander("가격대 설정", expanded=False):
        # 가격대 슬라이더
        price_range = st.slider(
            "1인 기준 가격대를 선택해주세요",
            min_value=5000,
            max_value=200000,
            value=(5000, 200000),  # Default range
            step=5000,
            format="₩%d",
        )
        list_price = list(price_range)
        if list_price[-1] == 200000:
            list_price[-1] = 1000000
        chat_state.price_range = list_price
    # st.write(f"선택된 가격대: ₩{price_range[0]} ~ ₩{price_range[1]}")

def ref_dropdown():
    # Default mode
    with st.expander("나이대 선택", expanded=False):
        ss.default_mode = st.selectbox(
            "나이대를 선택해주시면 더 맞춤형 서비스를 제공해드리겠습니다.",
            mode_options,
            index=0,
            # label_visibility="collapsed",
        )
        cmd_prefix, cmd_prefix_explainer, _ = age_options[ss.default_mode]
        st.caption(cmd_prefix_explainer)

def hashtag():
    with st.expander("식당 해시태그", expanded=False):
        # 예시 해시태그 리스트
        if 'hashtags' not in ss:
            ss.hashtags = [
                "#분위기맛집 🌟",  # 분위기가 좋은 맛집을 강조
                "#존맛 😋",       # 맛의 탁월함을 강조
                "#서비스굿굿 👍",  # 서비스의 품질을 강조
                "#가성비갑 💸",    # 가격 대비 만족도를 강조
                "#푸짐한음식량 🍽️",  # 음식의 양을 강조
                "#연인과함께 💑",  # 연인과의 방문을 추천
                "#다양한메뉴 📜",   # 메뉴 선택의 폭을 강조
                "#만족도200프로 😊", # 고객 만족도를 강조
                "#청결도최상 🧼",  # 위생과 청결을 강조
                "#주차편리 🚗",    # 주차의 편리함을 강조
                "#위치편리 📍"    # 접근성의 용이함을 강조
            ]

        # 사용자 정의 태그 입력
        custom_tag = st.text_input("나만의 해시태그 추가", placeholder="#맛집", key="custom_tag")
        add_button = st.button("추가", key="add_tag")
        if custom_tag and not custom_tag.startswith("#"):
            custom_tag = "#" + custom_tag
        if add_button and custom_tag:
            if custom_tag not in ss.hashtags:
                ss.hashtags.append(custom_tag)
                st.success(f"{custom_tag} 추가됨!")

        # 선택된 태그 상태 관리
        if 'selected_tags' not in st.session_state:
            ss.selected_tags = []

        # 해시태그 버튼 생성
        cols = st.columns(3)
        for i, tag in enumerate(st.session_state.hashtags):
            if cols[i % 3].button(tag, key=f"tag_{i}"):
                if tag in st.session_state.selected_tags:
                    st.session_state.selected_tags.remove(tag)
                elif len(st.session_state.selected_tags) < 3:
                    st.session_state.selected_tags.append(tag)
                else:
                    st.warning("최대 3개까지만 선택할 수 있습니다.")

        # 선택된 태그 표시 및 관리
        st.markdown("### 우선순위 최대 3가지")
        for n, tag in enumerate(ss.selected_tags):
            # 각 태그에 대한 컬럼을 생성
            col1, col2 = st.columns([3, 1])  # 비율을 조정하여 태그 이름과 삭제 버튼의 크기를 조절

            # 태그를 보여주는 컬럼
            with col1:
                st.markdown(f"**⭐️ {n+1}순위 : {tag}**")

            # 삭제 버튼을 보여주는 컬럼
            with col2:
                if st.button("❌", key=f"remove_{tag}"):  # 간단한 아이콘을 사용하여 공간 활용을 최적화
                    ss.selected_tags.remove(tag)
                    st.rerun()  # 페이지를 재실행하여 변경사항 적용

            chat_state.selected_tags = ss.selected_tags

def side_bar():
    ####### Sidebar #######
    with st.sidebar:
        st.subheader("Tamla's Flavor_" + VERSION)

        # chat_state 설정 
        chat_state.selected_age_groups = [list(age_options.keys())[1]]
        chat_state.gender = None
        chat_state.selected_foods = []
        chat_state.car = None

        # user 이름 설정
        user_id_setting()

        # Clear chat history
        def clear_chat_history():
            ss.messages = []
        # 대화창 초기화 설명
        st.write("#### 👇 대화창을 초기화하려면 아래 버튼을 클릭하세요.")
        # 초기화 버튼
        if st.button('Clear Chat History'):
            clear_chat_history()

        # 멘트 추가 
        st.write("#### 👇 아래에서 좋아하는 맛집 특성을 선택하시면, 당신을 위한 맞춤 맛집을 찾아드릴게요! 🌟")

        # 차 여부 
        # car() 

        # 식당 테마
        hashtag()

        # 성별 설정 
        # gender()

        # 나이대 설정 
        # age()

        # 가격대 설정 
        price()

        # food_selection
        # food_selection()

    
def title_header(logo, title):
    # 이미지와 제목을 포함한 컨테이너 생성
    header = st.container()

    with header:
        # 두 열로 나누기
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # 첫 번째 열에 로고 이미지 표시
            st.image(logo, width=300)  # 너비를 조절하여 크기 조정
        
        with col2:
            # 두 번째 열에 제목 텍스트 표시
            st.markdown(f"# {title}")  # 큰 글씨로 제목 표시
        
def format_robot_response(message):
    return f'''<div style="background-color: #fff3e0; padding: 15px; border-radius: 8px; border: 1px solid #ffb74d; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #e65100; box-shadow: 0 4px 8px rgba(0,0,0,0.1); font-size: 16px;">
        <strong>🍊:</strong> {message} </div>'''

def llm_method_button(eng_flag):
    # Show sample queries
    clicked_sample_query = None
    for _ in range(2):
        st.write("")

    if eng_flag:
        cols = ss.sample_queries
    else:
        cols = ss.sample_queries_kor

    for i, (btn_col, sample_query) in enumerate(zip(st.columns(2), cols)):
        with btn_col:
            if st.button(sample_query[:2], key=f"query{i}"):
                clicked_sample_query = sample_query[-2:]   

    parsed_query = parse_query(clicked_sample_query)
    chat_state.update(parsed_query=parsed_query)

    # chat_input_text = f"[{ss.default_mode}] " if cmd_prefix else ""
    # chat_input_text = limit_num_characters(chat_input_text + coll_name_as_shown, 35) + "/"
    # full_query = st.chat_input(chat_input_text)    

def questions_recommending():
    if 'clicked_query' not in ss:
        ss.clicked_query = None

    # 질문지 생성
    parsed_query = parse_query("", predetermined_chat_mode=ChatMode.CHAT_QUESTION_ID)
    chat_state.update(parsed_query=parsed_query)
    question_lists = get_bot_response(chat_state)

    # Show sample queries
    for _ in range(5):
        st.write("")

    def click_button(query):
        ss.clicked_query = query

    for i, (btn_col, sample_query) in enumerate(zip(st.columns(2), question_lists)):
        with btn_col:
            st.button(sample_query, key=f"query{i}", on_click=click_button, args=(sample_query,))

    clicked_sample_query = ss.clicked_query
    ss.clicked_query = None  # Reset for next use
    return clicked_sample_query

def url_setting(title, addr):    
    id_url, booking, img, menu_tags, feature_tags, review, revisit, reservation, companion, waiting_time, review_count = df_filter(title, addr)
    content = display_store_info(id_url, booking, img, menu_tags, feature_tags, review, revisit, reservation, companion, waiting_time, review_count)

    # 이미지가 있을 경우 사진 추가 (클릭 시 새 창에서 원본 보기)
    image_html = ""
    if img and img.strip():
        image_html = f"""
            <div>
                <a href="{id_url}" target="_blank">
                    <img src="{img}" alt="Store Image" style="width: 100%; max-width: 600px; max-height: 130px; object-fit: cover; border-radius: 10px; margin-bottom: 10px;">
                </a>
            </div>
        """

    # 최종 HTML을 Markdown에 적용
    st.markdown(f"""
        <div style="border:1px solid #ddd; border-radius:5px; padding:10px; margin-bottom:10px;">
            <div>{image_html}</div>
            <details>
                <summary style="cursor: pointer; font-size: 1.2em; font-weight: bold;">🍊 {title} 정보</summary>
                <div style="padding-top: 10px;">
                    {content}
                </div>
            </details>
        </div>
        """, unsafe_allow_html=True)

def main():
    if tmp := os.getenv("STREAMLIT_WARNING_NOTIFICATION"):
        st.warning(tmp)    

    side_bar()

    # 로고 이미지 로드
    logo = Image.open("media/탐라logo_w_horizon.png")

    # 세션 상태에 페이지 상태 초기화
    if 'page' not in ss:
        ss.page = 'language_select'

    # url_setting("제주그때그집 노형점", "제주 제주시 노형동 1045-11번지 1층")
    
    # 언어 선택 페이지
    if ss.page == 'language_select':
        st.title("🍊 환영합니다 / Welcome!")
        st.write("선호하는 언어를 선택하세요 / Choose your preferred language")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("한국어", use_container_width=True):
                ss.language = "한국어"
                ss.page = 'main_app'
                st.rerun()
        
        with col2:
            if st.button("English", use_container_width=True):
                ss.language = "English"
                ss.page = 'main_app'
                st.rerun()
    
    # 메인 앱 페이지
    elif ss.page == 'main_app':
        if ss.language == "English":
            title_header(logo, "")
            st.title("Welcome to the Culinary Journey with Tamna's Flavor AI!")
            # English content here
            st.markdown(GREETING_MESSAGE_ENG)
            # 날씨, 시간에 따른 인사말 생성 및 저장
            if 'greeting_message' not in ss:
                chat_state.flag = "영어로"                 
                parsed_query = parse_query("", predetermined_chat_mode=ChatMode.JUST_CHAT_GREETING_ID)
                chat_state.update(parsed_query=parsed_query)
                ss.greeting_message = get_bot_response(chat_state)

            # 사용자 ID를 포함한 전체 메시지 생성
            full_message = f"{chat_state.user_id}님 {ss.greeting_message}" if chat_state.user_id and chat_state.user_id.strip() else ss.greeting_message

            # 채팅 히스토리에 새 메시지 추가
            if full_message not in [msg for _, msg in chat_state.chat_history]:
                chat_state.chat_history.append(("", full_message))
                chat_state.chat_history_all.append(("", full_message))
                chat_state.sources_history.append(None)
            st.markdown(format_robot_response(full_message), unsafe_allow_html=True)

            open_ai_chat(eng_flag=True)
    
        else:
            title_header(logo, "")
            st.title("탐라는 맛 AI와 함께하는 미식 여행에 오신 것을 환영합니다!")
            # Korean content here
            st.markdown(GREETING_MESSAGE_KOR)
            # 날씨, 시간에 따른 인사말 생성 및 저장
            if 'greeting_message' not in ss:
                chat_state.flag = ""
                parsed_query = parse_query("", predetermined_chat_mode=ChatMode.JUST_CHAT_GREETING_ID)
                chat_state.update(parsed_query=parsed_query)
                ss.greeting_message = get_bot_response(chat_state)
                
            # 사용자 ID를 포함한 전체 메시지 생성
            full_message = f"{chat_state.user_id}님 {ss.greeting_message}" if chat_state.user_id and chat_state.user_id.strip() else ss.greeting_message

            # 채팅 히스토리에 새 메시지 추가
            if full_message not in (msg for _, msg in chat_state.chat_history):
                chat_state.chat_history.append(("", full_message))
                chat_state.chat_history_all.append(("", full_message))
                chat_state.sources_history.append(None)
            st.markdown(format_robot_response(full_message), unsafe_allow_html=True)

            open_ai_chat()  
            


if __name__ == '__main__':
    main()  
