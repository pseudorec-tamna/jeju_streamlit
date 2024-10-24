
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
from utils.prompts import chat_prompt_template, recommendation_prompt_template, multi_turn_prompt_template, recommendation_keyword_prompt_template

from recommendation.prompt import sub_task_detection_prompt
from recommendation.utils import json_format
# from colorama import Fore, Style
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain.memory import ConversationBufferWindowMemory
from recommendation.utils import sub_task_detection
from recommendation.distance_based import distance_based_recommendation, get_coordinates_by_question, coordinates_based_recommendation
import requests, time
import subprocess
from recommendation.sql_based import extract_sql_query, sql_based_recommendation
from recommendation.prompt import template_sql_prompt
from recommendation.context_based import context_based_recommendation

from utils.client import MysqlClient
# from tamla import load_memory
from utils.lang_utils import pairwise_chat_history_to_msg_list
import numpy as np
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from langchain_community.embeddings.huggingface import HuggingFaceEmbeddings


# df = pd.read_csv("./data/additional_info.csv", encoding='cp949')
# df = df.drop_duplicates(subset=["MCT_NM"], keep="last")
# df = df.reset_index(drop=True)

# database = pd.read_csv("./data/JEJU_MCT_DATA_v2.csv", encoding='cp949')
# meta_info = database.drop_duplicates(subset=["MCT_NM"], keep="last")
mysql = MysqlClient()

query = f"select * from tamdb.basic_info_1"
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

# documents = []
# for row in df.iterrows():
#   document = Document(
#       page_content=f"""name:{row[1]['MCT_NM']}, 
#       review_summary:{row[1]['review']},
#       full_location:{row[1]['ADDR']}, 
#       location:{row[1]['ADDR_detail']}, 
#       average_score:{row[1]['average_score']}, 
#       average_price:{row[1]['mean_price']},
#       payment_method:{row[1]['payment']}, 
#       review_counts: {row[1]['v_review_cnt']},
#       menu_info:{row[1]['menu_tags']}, 
#       feature_info:{row[1]['feature_tags']},
#       revisit_info:{row[1]['revisit']},
#       reservation_info:{row[1]['reservation']},
#       companion_info:{row[1]['companion']},
#       waiting_info:{row[1]['waiting_time']},
#       type: {row[1]['MCT_TYPE']}
#       """,
#       metadata={
#         "name":row[1]['MCT_NM'], 
#                 "review_summary":row[1]['review'],
#                 "full_location":row[1]['ADDR'],
#                 "location":row[1]['ADDR_detail'], 
#                 "average_score":row[1]['average_score'], 
#                 "average_price":row[1]['mean_price'],
#                 "payment_method":row[1]['payment'], 
#                 "review_counts": row[1]['v_review_cnt'],
#                 "menu_info":row[1]['menu_tags'], 
#                 "feature_info":row[1]['feature_tags'],
#                 "revisit_info":row[1]['revisit'],
#                 "reservation_info":row[1]['reservation'],
#                 "companion_info":row[1]['companion'],
#                 "waiting_info":row[1]['waiting_time'],
#                 "type": row[1]['MCT_TYPE']
#       }
#   )
#   documents.append(document)
å
#



def load_memory(input, chat_state):

    memory_vars = chat_state.memory.load_memory_variables({})
    memory_vars["chat_history"] = pairwise_chat_history_to_msg_list(chat_state.chat_history)

    return memory_vars.get("chat_history", [])

def get_hw_response(chat_state: ChatState):

    llm = ChatGoogleGenerativeAI(
        model=chat_state.bot_settings.llm_model_name,
        google_api_key=chat_state.google_api_key,
    )

    # 벡터DB 로드
    hugging_vectorstore = chat_state.vectorstore
    hugging_retriever_baseline = hugging_vectorstore.as_retriever()

    print(f"chat_state.info_menuplace: {chat_state.info_menuplace}")
    
    
    # 질의 분류
    response = sub_task_detection(
        chat_state.message, 
        chat_state.info_location, 
        chat_state.info_menuplace, 
        chat_state.info_keyword,
        chat_state.original_question
    )
    print('여기서부터 분석 시작')

    print('------')
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
    
    for keyword in ["근처", "가까운"]: 
        if (chat_state.message.find(keyword) != -1) and (response_type != 'Multi-turn'): 
            response_type = json_format(response)["response_type"] = "Distance-based"
    
    menuplace = chat_state.info_menuplace = recommendation_factors['menu_place'] = list(set(recommendation_factors['menu_place'] + chat_state.info_menuplace))
    location = chat_state.info_location = recommendation_factors['location'] = recommendation_factors['location'] if (chat_state.info_location == '' or chat_state.info_location == recommendation_factors['location']) else chat_state.info_location + recommendation_factors['location']
    keyword = chat_state.info_keyword = recommendation_factors['keyword'] = list(set(recommendation_factors['keyword'] + chat_state.info_keyword))
    business_type = chat_state.info_business_type = recommendation_factors['business_type'] = list(set(recommendation_factors['business_type'] + chat_state.info_business_type))

    
    if response_type == "Chat":
        chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | chat_prompt_template | llm | StrOutputParser()
        result = chain.invoke({"question": chat_state.message})
        rec = None # 변수 초기화
        return {'answer': result, 'title': '', 'address': ''}    

    elif response_type == "Distance-based":
        # coord = get_coordinates_by_question(chat_state.message)

        st.write("어느 위치에서 출발하시나요? 정확한 주소를 지도에서 검색 후 클릭해주세요.")
        st.components.v1.iframe('http://127.0.0.1:5000', width=650, height=600)
        
        while True: 
            response = requests.get('http://127.0.0.1:5000/get_coordinates')
            coordinates = response.json()
            latitude = coordinates['latitude']
            longitude = coordinates['longitude']
            
            print(latitude)
            print(longitude)
            if latitude is not None and longitude is not None:
                break
            time.sleep(5)
        
        rec = coordinates_based_recommendation((longitude, latitude), df)
        mct_nm_list = rec["MCT_NM"].tolist()

        row = []
        hugging_retriever_distance = hugging_vectorstore.as_retriever(
            search_kwargs={
                'filter': {
                    "name": {"$in": mct_nm_list}  # "name" 필드가 mct_nm_list에 포함되는지 확인
                }
            }
        )
        # print("chat_state.message", chat_state.message)
        docs = hugging_retriever_distance.invoke(chat_state.message)
        for doc in docs:
            row.append(doc.metadata)
        rec = pd.DataFrame(row).reset_index()

        # 문서가 없는 경우
        if len(rec) == 0:
            # fall back
            docs = hugging_retriever_baseline.invoke(chat_state.message)
            for doc in docs:
                row.append(doc.metadata)
            rec = pd.DataFrame(row).reset_index()



        chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state))|  recommendation_keyword_prompt_template | llm | StrOutputParser()
        result = chain.invoke({"question": original_question, "recommendations": rec.iloc[0].astype(str)})

        # 추천 후 초기화
        chat_state.info_menuplace = ['']
        chat_state.info_location = ''
        chat_state.info_keyword = ['']
        chat_state.info_business_type = ['']
        chat_state.original_question = ''

        # 마르코프 추가
        next_rec = None
        # if isinstance(rec, pd.DataFrame):
        id_t = df[df["MCT_NM"]==rec.iloc[0]["name"]].id.values[0] # id 값
        if id_t in transition_matrix_df.index:      # id가 ts매트릭스로 오면 
            next_rec = context_based_recommendation(id_t, transition_matrix_df, visit_poi_df)   
            
        return {
            'answer': result, 
            'title': rec['name'][:min(3, len(rec['name']))].tolist(), 
            'address': rec['full_location'][:min(3, len(rec['full_location']))].tolist(),
            'next_rec': next_rec
        }

        
    elif response_type == "Keyword-based":
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
        hugging_retriever = hugging_vectorstore.as_retriever(
            search_type='similarity',
            search_kwargs={
                'filter': {
                    "$or": [{"location": "제주"}] + [{"location": loc} for loc in filtered_location]+[{"type":business}for business in business_type]
                }
            }
        )
        row = []
        # 키워드를 넣어 문서 검색
        docs = hugging_retriever.invoke(location + ' '.join(keyword) + ' '.join(menuplace))
        for doc in docs:
            row.append(doc.metadata)
        rec = pd.DataFrame(row).reset_index()
        chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state))|  recommendation_keyword_prompt_template | llm | StrOutputParser()
        
        # 검색이 안된 경우
        if len(rec) ==0:
            # fall back
            docs = hugging_retriever_baseline.invoke(location + ' '.join(keyword) + ' '.join(menuplace))
            for doc in docs:
                row.append(doc.metadata)
            rec = pd.DataFrame(row).reset_index()
            
        chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state))|  recommendation_keyword_prompt_template | llm | StrOutputParser()
        result = chain.invoke({"question": original_question, "recommendations": rec.iloc[0].astype(str)})
        
        # 추천 후 초기화
        chat_state.info_menuplace = ['']
        chat_state.info_location = ''
        chat_state.info_keyword = ['']
        chat_state.info_business_type = ['']
        chat_state.original_question = ''
        
        
        # 마르코프 추가
        next_rec = None
        id_t = df[df["MCT_NM"]==rec.iloc[0]["name"]].id.values[0] # id 값
        if id_t in transition_matrix_df.index:      # id가 ts매트릭스로 오면 
            next_rec = context_based_recommendation(id_t, transition_matrix_df, visit_poi_df)   

        return {
            'answer': result, 
            'title': rec['name'][:min(3, len(rec['name']))].tolist(), 
            'address': rec['full_location'][:min(3, len(rec['full_location']))].tolist(),
            'next_rec': next_rec
        }
    elif response_type == "Multi-turn":
        chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | multi_turn_prompt_template | llm | StrOutputParser()
        print(f"멀티턴 - 추천요소:::: location:{location}\nmenu_place:{menuplace}\nkeyword:{keyword}")
        result = chain.invoke({"question": chat_state.message, "menuplace": menuplace, "location": location, "keyword":keyword})
        return {'answer': result, 'title': '', 'address': '', 'next_rec': ''}
    else: 
        pass 
        

    return response
