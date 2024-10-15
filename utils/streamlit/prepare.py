import os

import streamlit as st

from components.llm import CallbackHandlerDDGConsole
# from docdocgo import do_intro_tasks
from utils.chat_state import ChatState
from utils.prepare import GEMINI_API_KEY
# from utils.streamlit.fix_event_loop import remove_tornado_fix
# from utils.type_utils import OperationMode
from utils.streamlit.helpers import mode_options
from utils.type_utils import OperationMode
from langchain.memory import ConversationBufferWindowMemory


def prepare_app():
    if os.getenv("STREAMLIT_SCHEDULED_MAINTENANCE"):
        st.markdown("Welcome to Tamla's Flavor! 🍊")
        st.markdown(
            "Scheduled maintenance is currently in progress. Please check back later."
        )
        st.stop()

    # Flag for whether or not the OpenAI API key has succeeded at least once
    st.session_state.llm_api_key_ok_status = False

    print("query params:", st.query_params)
    st.session_state.update_query_params = None
    st.session_state.init_collection_name = st.query_params.get("collection")
    st.session_state.access_code = st.query_params.get("access_code")
    
    try:
        pass
        # remove_tornado_fix()
        # vectorstore = do_intro_tasks(openai_api_key=DEFAULT_OPENAI_API_KEY)
    except Exception as e:
        st.error(
            "Apologies, I could not load the vector database. This "
            "could be due to a misconfiguration of the environment variables "
            f"or missing files. The error reads: \n\n{e}"
        )
        st.stop()

    st.session_state.chat_state = ChatState(
        operation_mode=OperationMode.STREAMLIT,
        callbacks=[
            CallbackHandlerDDGConsole(),
            "placeholder for CallbackHandlerDDGStreamlit",
        ],
        google_api_key=GEMINI_API_KEY,
    )

    st.session_state.memory = ConversationBufferWindowMemory(k=5, 
                                                             memory_key="chat_history", 
                                                             return_messages=True)


    st.session_state.prev_supplied_gemini_api_key = None
    st.session_state.gemini_api_key = GEMINI_API_KEY
    if st.session_state.gemini_api_key == "DUMMY NON-EMPTY VALUE": # DUMMY_OPENAI_API_KEY_PLACEHOLDER:
        st.session_state.gemini_api_key = ""

    st.session_state.idx_file_upload = -1
    st.session_state.uploader_form_key = "uploader-form"

    st.session_state.idx_file_download = -1
    st.session_state.downloader_form_key = "downloader"

    st.session_state.user_avatar = os.getenv("USER_AVATAR") or None
    st.session_state.bot_avatar = os.getenv("BOT_AVATAR") or None  # TODO: document this

    SAMPLE_QUERIES_KOR = os.getenv(
        "SAMPLE_QUERIES_KOR",
        "/일반 추천 모드, /집계 모드, /gen_llm, /text_2_sql_llm"
    )
    st.session_state.sample_queries_kor = [q.strip() for q in SAMPLE_QUERIES_KOR.split(",")]

    SAMPLE_QUERIES = os.getenv(
        "SAMPLE_QUERIES",
        "/General Recommendation Mode, /Aggregation Mode, /gen_llm, /text_2_sql_llm"
    )
    st.session_state.sample_queries = [q.strip() for q in SAMPLE_QUERIES.split(",")]
    st.session_state.default_mode = mode_options[0]