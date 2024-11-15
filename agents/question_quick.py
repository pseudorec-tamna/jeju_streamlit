from datetime import datetime

from utils.chat_state import ChatState
from utils.prompts import CHAT_QUESTION_PROMPT
from langchain_google_genai import ChatGoogleGenerativeAI
from utils.lang_utils import pairwise_chat_history_to_msg_list
from langchain_core.runnables import RunnablePassthrough
import json 
import re


def load_memory(input, chat_state):
    # print("chat_state:", chat_state.memory)
    # print("chat_history : ", chat_state.chat_history[-1])
    return pairwise_chat_history_to_msg_list([chat_state.chat_history[-3]]) if chat_state.chat_history else []

def get_question_chat_chain(
    chat_state: ChatState,
    prompt_qa=CHAT_QUESTION_PROMPT,
):
    flag = chat_state.flag

    llm = ChatGoogleGenerativeAI(
        model=chat_state.bot_settings.llm_model_name,
        google_api_key=chat_state.google_api_key,
    )

    print("--Question LLM START")
    chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | prompt_qa | llm
    result = chain.invoke({
        "flag":flag
    })
    print("--Question LLM END")    

    # 결과를 파싱하여 리스트로 변환
    content = result.content
    try:
        # JSON 형식으로 파싱 시도
        questions = json.loads(content)
    except json.JSONDecodeError:
        # JSON 파싱 실패 시 정규표현식으로 추출 시도
        pattern = r'"([^"]*)"'
        questions = re.findall(pattern, content)

    # 항상 3개의 질문을 반환하도록 보장
    if len(questions) < 2:
        questions.extend(["추가 질문이 필요합니다."] * (2 - len(questions)))
    elif len(questions) > 2:
        questions = questions[:2]

    return questions
