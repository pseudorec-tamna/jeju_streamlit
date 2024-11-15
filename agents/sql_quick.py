
import pandas as pd
import google.generativeai as genai
import os
import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from utils.chat_state import ChatState
from utils.prompts import chat_prompt_template, recommendation_sql_prompt_template

from langchain_core.runnables import RunnablePassthrough
from recommendation.sql_based import extract_sql_query, sql_based_recommendation
from recommendation.prompt import template_sql_prompt
from utils.client import MysqlClient
# from tamla import load_memory
from utils.lang_utils import pairwise_chat_history_to_msg_list
from agents.hyeonwoo import sub_task_detection, json_format

mysql = MysqlClient()

query = f"select * from tamdb.basic_info_1"
mysql.cursor.execute(query)
rows = mysql.cursor.fetchall()
columns = [i[0] for i in mysql.cursor.description]  # 컬럼 이름 가져오기
df_quan = pd.DataFrame(rows, columns=columns)
# df = df.merge(meta_info[["MCT_NM", "ADDR", "MCT_TYPE"]], how="left", on=["MCT_NM","ADDR"])

def load_memory(input, chat_state):
    # print("chat_state:", chat_state.memory)
    memory_vars = chat_state.memory.load_memory_variables({})
    memory_vars["chat_history"] = pairwise_chat_history_to_msg_list(chat_state.chat_history)
    # print("chat_history:", memory_vars["chat_history"])
    # memory_vars.get("chat_history", [])
    return memory_vars.get("chat_history", [])

def get_sql_chat(chat_state: ChatState):
    # 한국어 Or 영어
    flag_eng = chat_state.flag_eng

    # Initialize the Gemini 1.5 Flash LLM
    llm = ChatGoogleGenerativeAI(
        model=chat_state.bot_settings.llm_model_name,
        google_api_key=chat_state.google_api_key,
    )
    print(f"chat_state.info_menuplace: {chat_state.info_menuplace}")

    # 질의 분류
    response = sub_task_detection(
        chat_state.message, 
        chat_state.info_location, 
        chat_state.info_menuplace, 
        chat_state.info_keyword,
        chat_state.original_question
    )
    if response == '': # 욕설 등으로 인해서 출력이 제대로 완성되지 않은 경우 
        # 여기에 어떤 내용을 채울지에 대한 고민 
        return {'answer': '', 'title': '', 'address': '', 'next_rec': ''}

    # 질의 유형 
    response_type = json_format(response)["response_type"]

    # 질의 요소 
    recommendation_factors = json_format(response)["recommendation_factors"]

    # 필요 질의문 보관
    original_question = chat_state.original_question = json_format(response)["original_question"]
    
    print(f"답변 타입: {response_type}")
    print('답변', json_format(response))
    if (recommendation_factors['location'] == '제주' or recommendation_factors['location'] == '제주도') and response_type == "Keyword-based":
        recommendation_factors['location'] = ''
        response_type = "Multi-turn"
    
    menuplace = chat_state.info_menuplace = recommendation_factors['menu_place'] = list(set(recommendation_factors['menu_place'] + chat_state.info_menuplace))
    location = chat_state.info_location = recommendation_factors['location'] = recommendation_factors['location'] if (chat_state.info_location == '' or chat_state.info_location == recommendation_factors['location']) else chat_state.info_location + recommendation_factors['location']
    keyword = chat_state.info_keyword = recommendation_factors['keyword'] = list(set(recommendation_factors['keyword'] + chat_state.info_keyword))
    business_type = chat_state.info_business_type = recommendation_factors['business_type'] = list(set(recommendation_factors['business_type'] + chat_state.info_business_type))
    query_rewrite = chat_state.query_rewrite = recommendation_factors["query_rewrite"] 
    
    if response_type == "Chat":
        chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | chat_prompt_template | llm | StrOutputParser()
        result = chain.invoke({"question": chat_state.message, "flag_eng":flag_eng})
        rec = None # 변수 초기화
        return {'answer': result, 'title': '', 'address': '', 'next_rec':''}
    else:
        try:
            chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | recommendation_sql_prompt_template | llm | StrOutputParser()
            sql_prompt = ChatPromptTemplate.from_template(
                template_sql_prompt
                )
            sql_chain = sql_prompt | llm 
            print("\nSQL-QUERY REWRITE :", query_rewrite)
            output = sql_chain.invoke({"question": query_rewrite}) # sql 출력
            print("SQL:", output.content)
            rec = sql_based_recommendation(output, df_quan)             # 문서 검색
            print(rec['recommendation'].iloc[:3].to_markdown())
            result = chain.invoke({"question": chat_state.message, "recommendations": rec['recommendation'].iloc[:3].to_markdown(), "flag_eng":flag_eng, "tmp":rec['tmp']})

            # 추천 후 초기화
            chat_state.info_menuplace = ['']
            chat_state.info_location = ''
            chat_state.info_keyword = ['']
            chat_state.info_business_type = ['']
            chat_state.original_question = ''
            
            print(f"답변 타입: 정량 모델")
            print('여기서의 응답', result)
            response = {
                    "answer": result, 
                    'title': rec['recommendation']['MCT_NM'].iloc[:min(3, len(rec['recommendation']))].tolist(), 
                    'address': rec['recommendation']['ADDR'].iloc[:min(3, len(rec['recommendation']))].tolist(),
                    'next_rec': ''
                }
            print('응답', response)
            return response
        except Exception as e:
            print(f"An error occurred: {e}")
            # 추천 후 초기화
            chat_state.info_menuplace = ['']
            chat_state.info_location = ''
            chat_state.info_keyword = ['']
            chat_state.info_business_type = ['']
            chat_state.original_question = ''

            return {
                    "answer": "앗! 데이터 바다에서 추천을 건져오지 못했어요. 다른 질문으로 다시 시도해 보실래요?", 
                    'title': [], 
                    'address': [],
                    'next_rec': ''
                }
