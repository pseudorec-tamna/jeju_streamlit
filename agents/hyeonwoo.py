
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
from utils.prompts import chat_prompt_template, recommendation_prompt_template, recommendation_sql_prompt_template, item_search_prompt_template, explanation_template, multi_turn_template

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
from sentence_transformers import SentenceTransformer


# df = pd.read_csv("./data/additional_info.csv", encoding='cp949')
# df = df.drop_duplicates(subset=["MCT_NM"], keep="last")
# df = df.reset_index(drop=True)


database = pd.read_csv("./data/JEJU_MCT_DATA_v2.csv", encoding='cp949')
meta_info = database.drop_duplicates(subset=["MCT_NM"], keep="last")


mysql = MysqlClient()
query = f"select * from tamdb.detailed_info_1"
mysql.cursor.execute(query)
rows = mysql.cursor.fetchall()
columns = [i[0] for i in mysql.cursor.description]  # 컬럼 이름 가져오기
df = pd.DataFrame(rows, columns=columns)
df = df.merge(meta_info[["ADDR", "MCT_TYPE"]], how="left", on="ADDR")

# # 정보 없는 가게 모두 제거
# df['title'].replace('', np.nan, inplace=True)
# df= df.dropna(subset='title')

path_visit_additional_info = './data/poi_df.csv' # 방문이력 데이터에 대한 id 크롤링 따로 진행
path_transition_matrix = './data/transition_matrix.csv'


transition_matrix_df = pd.read_csv(path_transition_matrix)
visit_poi_df = pd.read_csv(path_visit_additional_info)


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
    print(f"chat_state.info_menuplace: {chat_state.info_menuplace}")
    menuplace = chat_state.info_menuplace
    location = chat_state.info_location
    keyword = chat_state.info_keyword
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
        
    elif response_type == "Recommendation" or response_type == "User Preference Elicitation":

        print(f"추천 타입:{json_format(response)["recommendation_type"]}")
        print(f"추천 요소:{json_format(response)["recommendation_factors"]}")
        menuplace = chat_state.info_menuplace = json_format(response)["recommendation_factors"]['menu_place']
        location = chat_state.info_location = json_format(response)["recommendation_factors"]['location']
        keyword = chat_state.info_keyword = json_format(response)["recommendation_factors"]['keyword']

        if json_format(response)["recommendation_type"] == "Distance-based":
            chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | recommendation_prompt_template | llm | StrOutputParser()
            coord = get_coordinates_by_question(chat_state.message)
            print("정확한 주소를 지도에서 검색후에 클릭해주세요 !!")

            from IPython.display import display, IFrame
            latitude, longitude = coord  # coord에서 위도와 경도 추출
            st.components.v1.iframe(src='http://127.0.0.1:5000', width=800, height=600)
            
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
            print('여기 조사', rec)
            result = chain.invoke({"question": chat_state.message, "recommendations": rec})  
            # response = {"answer": result}
            # return response

        elif json_format(response)["recommendation_type"] == "Attribute-based":
            chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | recommendation_sql_prompt_template | llm | StrOutputParser()
            sql_prompt = ChatPromptTemplate.from_template(template_sql_prompt)
            sql_chain = sql_prompt | llm
            output = sql_chain.invoke({"question": chat_state.message})            
            rec = sql_based_recommendation(output, df)
            print('attribute 응답:', rec)
            result = chain.invoke({"question": chat_state.message, "recommendations": rec, "search_info": output.content})

        elif json_format(response)["recommendation_type"] == "Keyword-based":
            chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | recommendation_prompt_template | llm | StrOutputParser()
            result = chain.invoke({"question": chat_state.message, "recommendations": df[30:40]})
            chat_state.info_menuplace = ['']
            chat_state.info_location = ''
            chat_state.info_keyword = ['']

        elif json_format(response)["recommendation_type"] == "Multi-turn":
            chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | multi_turn_template | llm | StrOutputParser()
            print(f"location:{location}\nmenu_place:{menuplace}\nkeyword:{keyword}")
            result = chain.invoke({"question": chat_state.message, "menuplace": menuplace, "location": location, "keyword":keyword})
        else: 
            pass 
        
        next_rec = None
        for id_t in rec['id'].values:
            if id_t in transition_matrix_df.index:
                next_rec = context_based_recommendation(id_t, transition_matrix_df, visit_poi_df)
        
    # elif response_type == "Item Detail Search":
    #     # SQL 문으로 검색 가능하도록 

    #     chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | item_search_prompt_template | llm | StrOutputParser()
    #     item_info = df.loc[df["MCT_NM"] == str(chat_state.message)].reset_index(drop=True)
    #     print("item_info:", item_info)
    #     result = chain.invoke({
    #         "question": chat_state.message,
    #         "MCT_NM": item_info["MCT_NM"],
    #         "ADDR": item_info["ADDR"],
    #         "tel": item_info["tel"],
    #         "booking": item_info["booking"]
    #         })
    elif response_type == "Explanation":
        chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | explanation_template | llm | StrOutputParser()
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
    print(f"답변 타입:{response_type}")
    print('여기서의 응답', result)
    response = {"answer": result}
    print('응답', response)

    return response
