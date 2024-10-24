
import pandas as pd
import google.generativeai as genai
import os
import streamlit as st
from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from utils.chat_state import ChatState
from utils.prompts import recommendation_keyword_prompt_template2, chat_prompt_template

from recommendation.utils import json_format
# from colorama import Fore, Style
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from recommendation.utils import sub_task_detection
from utils.client import MysqlClient
# from tamla import load_memory
from utils.lang_utils import pairwise_chat_history_to_msg_list
import numpy as np
from langchain_community.vectorstores import Chroma
from langchain.schema import Document

from langchain_community.embeddings.huggingface import HuggingFaceEmbeddings


# df = pd.read_csv("./data/additional_info.csv", encoding='cp949')
# df = df.drop_duplicates(subset=["MCT_NM"], keep="last")
# df = df.reset_index(drop=True)

# database = pd.read_csv("./data/JEJU_MCT_DATA_v2.csv", encoding='cp949')
# meta_info = database.drop_duplicates(subset=["MCT_NM"], keep="last")
mysql = MysqlClient()

query = f"select * from tamdb.basic_info"
mysql.cursor.execute(query)
rows = mysql.cursor.fetchall()
columns = [i[0] for i in mysql.cursor.description]  # 컬럼 이름 가져오기
df_quan = pd.DataFrame(rows, columns=columns)
# df = df.merge(meta_info[["MCT_NM", "ADDR", "MCT_TYPE"]], how="left", on=["MCT_NM","ADDR"])

query = f"select * from tamdb.detailed_info_1"
mysql.cursor.execute(query)
rows = mysql.cursor.fetchall()
columns = [i[0] for i in mysql.cursor.description]  # 컬럼 이름 가져오기
df = pd.DataFrame(rows, columns=columns)
df['ADDR_detail'] = df['ADDR'].map(lambda x: ' '.join(x.split(' ')[1:3]))
# df = df.merge(meta_info[["MCT_NM", "ADDR", "MCT_TYPE"]], how="left", on=["MCT_NM","ADDR"])


query = f"select * from tamdb.attraction_info"
mysql.cursor.execute(query)
rows = mysql.cursor.fetchall()
columns = [i[0] for i in mysql.cursor.description]  # 컬럼 이름 가져오기
df_refer = pd.DataFrame(rows, columns=columns)

path_visit_additional_info = './data/poi_df.csv' # 방문이력 데이터에 대한 id 크롤링 따로 진행
path_transition_matrix = './data/transition_matrix.csv'

transition_matrix_df = pd.read_csv(path_transition_matrix)
visit_poi_df = pd.read_csv(path_visit_additional_info)



# Embedding 모델 불러오기 - 개별 환경에 맞는 device로 설정
model_name = "upskyy/bge-m3-Korean"
model_kwargs = {
    # "device": "cuda"
    # "device": "mps"
    "device": "cpu"
}
encode_kwargs = {"normalize_embeddings": True}
hugging_embeddings = HuggingFaceEmbeddings(
    model_name=model_name,
    model_kwargs=model_kwargs,
    encode_kwargs=encode_kwargs,)

# hugging_vectorstore = Chroma.from_documents(
#     documents=documents,
#     embedding=hugging_embeddings,
#     persist_directory="./chroma_db"          # Save the embeddings at the first time
# )
hugging_vectorstore = Chroma(persist_directory="./chroma_db6", embedding_function=hugging_embeddings)        # Load the embeddings
hugging_retriever = hugging_vectorstore.as_retriever()


# print('렛츠고ㅇ', hugging_retriever.invoke('중문'))

def load_memory(input, chat_state):
    # print("chat_state:", chat_state.memory)
    memory_vars = chat_state.memory.load_memory_variables({})
    memory_vars["chat_history"] = pairwise_chat_history_to_msg_list(chat_state.chat_history)
    # print("chat_history:", memory_vars["chat_history"])
    # memory_vars.get("chat_history", [])
    return memory_vars.get("chat_history", [])

def get_keywords_chat(chat_state: ChatState):
# Initialize the Gemini 1.5 Flash LLM
    llm = ChatGoogleGenerativeAI(
        model=chat_state.bot_settings.llm_model_name,
        google_api_key=chat_state.google_api_key
    )
    print(f"chat_state.info_menuplace: {chat_state.info_menuplace}")
    menuplace = chat_state.info_menuplace
    location = chat_state.info_location
    keyword = chat_state.info_keyword
    business_type = chat_state.info_business_type

    response = sub_task_detection(chat_state.message, location, menuplace, keyword)

    response_type = json_format(response)["response_type"]
    print(f"답변 타입:{response_type}")
    print('답변', json_format(response))
    if response_type == "Chat":
        chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | chat_prompt_template | llm | StrOutputParser()
        print(chain)
        result = chain.invoke({"question": chat_state.message})
    # elif response_type == "User Preference Elicitation":
    #     chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | chat_prompt_template | llm
    #     result = chain.invoke({"question": chat_state.message})
        
    # elif response_type == "Recommendation" or response_type == "User Preference Elicitation":
        rec = None # 변수 초기화
        print(f"추천 타입:{json_format(response)['response_type']}")
        print(f"추천 요소:{json_format(response)['recommendation_factors']}")
        menuplace = chat_state.info_menuplace = json_format(response)["recommendation_factors"]['menu_place']
        location = chat_state.info_location = json_format(response)["recommendation_factors"]['location']
        keyword = chat_state.info_keyword = json_format(response)["recommendation_factors"]['keyword']
        business_type = chat_state.info_business_type = json_format(response)["recommendation_factors"]['business_type']    
        result = chain.invoke({"question": chat_state.message})  

        chat_state.info_menuplace = ['']
        chat_state.info_location = ''
        chat_state.info_keyword = ['']
        chat_state.info_business_type = ['']
        return {'answer': result}
    else:
        tmp_rank = [f"{i+1} 순위로 " + j for i, j in enumerate(chat_state.selected_tags)]
        selected_words = '\n'.join(tmp_rank) if chat_state.selected_tags else "None"

        menuplace = chat_state.info_menuplace = json_format(response)["recommendation_factors"]['menu_place']
        location = chat_state.info_location = json_format(response)["recommendation_factors"]['location']
        keyword = chat_state.info_keyword = json_format(response)["recommendation_factors"]['keyword']
        business_type = chat_state.info_business_type = json_format(response)["recommendation_factors"]['business_type']    

        print('\n\n\n\n호출됐음\n\n\n\n')
        # 정확한 주소 검색 후 못찾으면 contains로 검색 
        retrieved = df[df['ADDR_detail'] == location]
        if len(retrieved) == 0:
            retrieved = df[df['ADDR_detail'].str.contains(location)]
        
        if len(retrieved) == 0:
            retrieved = df[df['MCT_NM'] == location]

        if len(retrieved) == 0:
            retrieved = df[df['MCT_NM'].str.contains(location)]

        if len(retrieved) == 0:
            retrieved = df_refer[df_refer['MCT_NM'].str.contains(location)]

        filtered_location = retrieved['ADDR_detail'].unique()
        filtered_business_type = business_type
        print('수집된 location', filtered_location)
        print('수집된 busyness type', filtered_business_type)
        hugging_retriever = hugging_vectorstore.as_retriever(
            search_type='similarity',
            search_kwargs={
                'filter': {
                    "$or": [{"location": "제주"}] + [{"location": loc} for loc in filtered_location]+[{"type":business}for business in filtered_business_type]
                }
            }, 
        )
        print(hugging_retriever)
        row = []
        # print("chat_state.message", chat_state.message)
        docs = hugging_retriever.invoke(chat_state.message)
        print('docs', docs)
        for doc in docs:
            row.append(doc.metadata)
        rec = pd.DataFrame(row).reset_index()
        print('개수', len(rec))
        print('키워드 추천 문서:', rec.iloc[0].astype(str))
        chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state))|  recommendation_keyword_prompt_template2 | llm | StrOutputParser()
        result = chain.invoke({"question": chat_state.message, "recommendations": rec.iloc[0].astype(str), "selected_tags": selected_words})
        
        chat_state.info_menuplace = ['']
        chat_state.info_location = ''
        chat_state.info_keyword = ['']
        chat_state.info_business_type = ['']
        print('이게 문제', rec['name'][:min(3, len(rec['name']))].tolist())
        print('결과', {
            'answer': result, 
            'title': rec['name'][:min(3, len(rec['name']))].tolist(), 
            'address': rec['full_location'][:min(3, len(rec['full_location']))].tolist()
        })
        return {
            'answer': result, 
            'title': rec['name'][:min(3, len(rec['name']))].tolist(), 
            'address': rec['full_location'][:min(3, len(rec['full_location']))].tolist()
        }