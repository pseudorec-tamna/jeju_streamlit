
import pandas as pd
import google.generativeai as genai
import os

from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from utils.chat_state import ChatState
from utils.prompts import chat_prompt_template, recommendation_prompt_template, recommendation_sql_prompt_template, item_search_prompt_template

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

from recommendation.context_based import make_transition_matrix, context_based_recommendation, get_additional_info_visit_hist
from recommendation.content_based import get_summary, encode_poi_attributes, load_collection_db, content_based_recommendation

# from tamla import load_memory
from utils.lang_utils import pairwise_chat_history_to_msg_list
import streamlit as st 
from utils.client import MysqlClient


# df = pd.read_csv("./data/additional_info.csv", encoding='cp949')
# df = df.drop_duplicates(subset=["MCT_NM"], keep="last")
# df = df.reset_index(drop=True)

# database = pd.read_csv("./data/JEJU_MCT_DATA_v2.csv", encoding='cp949')
# meta_info = database.drop_duplicates(subset=["MCT_NM"], keep="last")
# df = df.merge(meta_info[["MCT_NM", "MCT_TYPE"]], how="left", on="MCT_NM")

database = pd.read_csv("./data/JEJU_MCT_DATA_v2.csv", encoding='cp949')
meta_info = database.drop_duplicates(subset=["MCT_NM"], keep="last")

mysql = MysqlClient()
query = f"select * from tamdb.detailed_info_1"
mysql.cursor.execute(query)
rows = mysql.cursor.fetchall()
columns = [i[0] for i in mysql.cursor.description]  # 컬럼 이름 가져오기
df = pd.DataFrame(rows, columns=columns)
df = df.merge(meta_info[["ADDR", "MCT_TYPE"]], how="left", on="ADDR")


path_visit_info = './data/tn_visit_area_info_h.csv'
path_visit_additional_info = './data/poi_df.csv'
path_transition_matrix = './data/transition_matrix.csv'

init = False 
if init: # JEJU_MCT_DATA에 없는 방문이력 점포의 추가 정보 크롤링 (사전 진행))
    poi_df = get_additional_info_visit_hist(path_visit_info, path_visit_additional_info)
else:
    poi_df = pd.read_csv(path_visit_additional_info).iloc[:,1:]

hist_df = pd.read_csv(path_visit_info)
hist_df = hist_df[(hist_df.X_COORD > 126.117692) & (hist_df.X_COORD < 127.071811) & (hist_df.Y_COORD > 33.062919) & (hist_df.Y_COORD < 33.599581)]

poi_df = poi_df.rename(columns={'data-id':'id'})
removal_titles = ['호텔','리조트','아파트','빌라','독채','렌터카','학교','집','전원주택','편의점']
poi_df = poi_df[~poi_df.VISIT_AREA_NM.str.contains('|'.join(removal_titles))]
poi_df = poi_df[poi_df.id != 'no']

hist_df = hist_df[['TRAVEL_ID','VISIT_ORDER','VISIT_START_YMD','VISIT_AREA_NM','ROAD_NM_ADDR','LOTNO_ADDR']].merge(poi_df, on=['VISIT_AREA_NM','ROAD_NM_ADDR','LOTNO_ADDR'])
hist_df = hist_df[['TRAVEL_ID','id','VISIT_START_YMD','VISIT_ORDER','VISIT_AREA_NM']]
hist_df = hist_df[hist_df.id.isin(df.id.unique())] # 신한카드 관련 id만 활용

init = True
if init:
    transition_matrix_df = make_transition_matrix(hist_df, poi_df, df,path_transition_matrix)
else:
    transition_matrix_df = pd.read_csv(path_transition_matrix)

def load_memory(input, chat_state):
    # print("chat_state:", chat_state.memory)
    memory_vars = chat_state.memory.load_memory_variables({})
    memory_vars["chat_history"] = pairwise_chat_history_to_msg_list(chat_state.chat_history)
    # print("chat_history:", memory_vars["chat_history"])
    # memory_vars.get("chat_history", [])
    return memory_vars.get("chat_history", [])

def get_hw_response(chat_state: ChatState):
    # Initialize the Gemini 1.5 Flash LLM
    llm = ChatGoogleGenerativeAI(
        model=chat_state.bot_settings.llm_model_name,
        google_api_key=chat_state.google_api_key
    )
    
    response = sub_task_detection(chat_state.message)
    response_type = json_format(response)["response_type"]
    print("response_type:",response_type)

    if response_type == "Chat":
        chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | chat_prompt_template | llm
        result = chain.invoke({"question": chat_state.message})

    elif response_type == "Recommendation":
        
        if json_format(response)["recommendation_type"] == "Distance-based":
            chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | recommendation_prompt_template | llm
            coord = get_coordinates_by_question(chat_state.message)
            st.write("정확한 주소를 지도에서 검색후에 클릭해주세요 !!")
            print("정확한 주소를 지도에서 검색후에 클릭해주세요 !!")

            # from IPython.display import IFrame
            latitude, longitude = coord  # coord에서 위도와 경도 추출
            # display(IFrame(src='http://127.0.0.1:5000', width=1200, height=600))
            st.components.v1.iframe('http://127.0.0.1:5000', width=650, height=600)
            
            while True: 
                response = requests.get('http://127.0.0.1:5000/get_coordinates')
                coordinates = response.json()
                latitude = coordinates['latitude']
                longitude = coordinates['longitude']
                if latitude is not None and longitude is not None:
                    break
                time.sleep(5)
            
            rec = coordinates_based_recommendation((longitude, latitude), df)
            result = chain.invoke({"question": chat_state.message, "recommendations": rec})  
        elif json_format(response)["recommendation_type"] == "Attribute-based":
            chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | recommendation_sql_prompt_template | llm
            sql_prompt = ChatPromptTemplate.from_template(template_sql_prompt)
            sql_chain = sql_prompt | llm
            output = sql_chain.invoke({"question": chat_state.message})            
            rec = sql_based_recommendation(output, df)
            result = chain.invoke({"question": chat_state.message, "recommendations": rec, "search_info": output.content})  
        elif json_format(response)["recommendation_type"] == "Context-based":
            chain = RunnablePassthrough.assign(chat_history=load_memory) | recommendation_sql_prompt_template | llm
            # 기준이 되는 가맹점이 있어야함
            tmp_id = '1648347549'
            rec = context_based_recommendation(tmp_id, transition_matrix_df, shinhan_ids, other_ids)
            result = chain.invoke({"question": question+tmp_id, "recommendations": rec})  
        else: # Content-based
            chain = RunnablePassthrough.assign(chat_history=load_memory) | recommendation_sql_prompt_template | llm

            df_summary = get_summary(df)
            db_init = False
            if db_init == True:
                # 약 한시간 걸림
                encode_poi_attributes(df_summary)

            collection = load_collection_db()
            rec = content_based_recommendation(question, collection, df_summary)
            result = chain.invoke({"question": question, "recommendations": rec})  
    
    elif response_type == "Item Detail Search":
        # SQL 문으로 검색 가능하도록 

        chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | item_search_prompt_template | llm
        item_info = df.loc[df["MCT_NM"] == str(chat_state.message)].reset_index(drop=True)
        print("item_info:", item_info)
        result = chain.invoke({
            "question": chat_state.message,
            "MCT_NM": item_info["MCT_NM"],
            "ADDR": item_info["ADDR"],
            "tel": item_info["tel"],
            "booking": item_info["booking"]
            })
    else: 
        pass 
    response = {"answer": result.content}
    return response