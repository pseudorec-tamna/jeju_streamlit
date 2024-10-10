import os
import streamlit as st
from openai import OpenAI
from PIL import Image
from utils.prepare import (
    get_logger,
    DEFAULT_OPENAI_API_KEY
)
from utils.query_parsing import parse_query
from components.llm import CallbackHandlerDDGStreamlit
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
from utils.streamlit.helpers import (
    mode_options,
    mode_option_to_prefix,
    STAND_BY_FOR_INGESTION_MESSAGE,
    show_sources,
    show_downloader,
    fix_markdown,    
    show_uploader,
)
from streamlit_modal import Modal
from tamla import get_bot_response, jeju_greeting, jeju_weather_dict

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
    if "messages" not in ss:
        ss.messages = []

    for message in ss.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat 입력창 설명 
    if eng_flag == True:
        temp_prompt = st.chat_input("How can I assist you?")
    else:
        temp_prompt = st.chat_input("무엇을 도와드릴까요?")

    if prompt := temp_prompt:
        ss.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=ss.user_avatar):
            st.markdown(prompt)

        parsed_query = parse_query(prompt)
        chat_state.update(parsed_query=parsed_query)

        with st.chat_message("assistant", avatar=ss.bot_avatar):

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

            # Add the response to the chat history
            chat_state.chat_history.append((prompt, answer))


            message_placeholder.markdown(answer)
        ss.messages.append({"role": "assistant", "content": answer})
    # else:
    #     st.info("OpenAI API 키를 입력해주세요.", icon="🗝️")

def open_ai_api_setting():
    # st.sidebar.title("OpenAI API 설정")
    openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password")
    if not openai_api_key:
        chat_state.user_id = None
    else:
        chat_state.user_id = openai_api_key[:3]

    return openai_api_key

def user_id_setting(): 
    user_id = st.sidebar.text_input("User ID", 
                                    label_visibility='visible',
                                    disabled=False,
                                    placeholder="홍길동")
    if user_id == "":
        chat_state.user_id = None
    else:
        chat_state.user_id = user_id
        chat_state.chat_history.append(("사용자 이름: ", "앞으로 내 이름을 언급하면서, 친절하게 답변해줘. 내 이름: "+user_id))

    return user_id

def side_bar():
    ####### Sidebar #######
    with st.sidebar:
        st.subheader("Tamla's Flavor_" + VERSION)

        user_id = user_id_setting()

        # Default mode
        with st.expander("User Settings", expanded=True):
            ss.default_mode = st.selectbox(
                "Command used if none provided",
                mode_options,
                index=0,
                # label_visibility="collapsed",
            )
            cmd_prefix, cmd_prefix_explainer = mode_option_to_prefix[ss.default_mode]
            st.caption(cmd_prefix_explainer)
    
            
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
        <strong>🍊:</strong> {message}
    </div>'''
        
def main():
    if tmp := os.getenv("STREAMLIT_WARNING_NOTIFICATION"):
        st.warning(tmp)    

    side_bar()

    # 제주도 날짜 및 날씨 정보 가져오기 + greetings
    weather_dict = jeju_weather_dict()

    # 로고 이미지 로드
    logo = Image.open("media/탐라logo_w_horizon.png")

    # 세션 상태에 페이지 상태 초기화
    if 'page' not in ss:
        ss.page = 'language_select'
    
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
            st.title("Welcome to the Culinary Journey with Tamla's Flavor AI!")
            # English content here
            st.markdown(GREETING_MESSAGE_ENG)
            # 날씨, 시간, User
            greeting_meesgage = jeju_greeting(weather_dict, "영어로")
            if chat_state.user_id is not None:
                full_message = f"{chat_state.user_id}님 {greeting_meesgage}"
                # chat_state.chat_history.append((full_message, ""))
            else: 
                full_message = greeting_meesgage
            if full_message: 
                chat_state.chat_history.append((full_message, ""))
                chat_state.chat_history_all.append((None, full_message))
                chat_state.sources_history.append(None)

            st.markdown(format_robot_response(full_message), unsafe_allow_html=True)
            
            # st.write(
            #     "This is a simple chatbot that uses OpenAI's GPT-3.5 model to generate responses. "
            #     "To use this app, you need to provide an OpenAI API key, which you can get [here](https://platform.openai.com/account/api-keys)."
            # )

            # Show sample queries
            clicked_sample_query = None
            for _ in range(2):
                st.write("")
            for i, (btn_col, sample_query) in enumerate(zip(st.columns(2), ss.sample_queries)):
                with btn_col:
                    if st.button(sample_query, key=f"query{i}"):
                        clicked_sample_query = sample_query
            
            open_ai_chat(eng_flag=True)
        
        else:
            title_header(logo, "")
            st.title("탐라는 맛 AI와 함께하는 미식 여행에 오신 것을 환영합니다!")
            # Korean content here
            st.markdown(GREETING_MESSAGE_KOR)
            # 날씨, 시간, User
            greeting_meesgage = jeju_greeting(weather_dict)
            if chat_state.user_id is not None:
                full_message = f"{chat_state.user_id}님 {greeting_meesgage}"
            else:
                full_message = greeting_meesgage
            if full_message:
                chat_state.chat_history.append((full_message, ""))
                chat_state.chat_history_all.append((None, full_message))
                chat_state.sources_history.append(None)

            st.markdown(format_robot_response(full_message), unsafe_allow_html=True)             

            # Show sample queries
            clicked_sample_query = None
            for _ in range(2):
                st.write("")
            for i, (btn_col, sample_query) in enumerate(zip(st.columns(2), ss.sample_queries_kor)):
                with btn_col:
                    if st.button(sample_query, key=f"query{i}"):
                        clicked_sample_query = sample_query   


            open_ai_chat()


if __name__ == '__main__':
    main()  
