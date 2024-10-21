
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
# from tamla import load_memory
from utils.lang_utils import pairwise_chat_history_to_msg_list
import streamlit as st 
from utils.client import MysqlClient

mysql = MysqlClient()
query = f"select * from tamdb.detailed_info_1"
mysql.cursor.execute(query)
rows = mysql.cursor.fetchall()
columns = [i[0] for i in mysql.cursor.description]  # 컬럼 이름 가져오기
df = pd.DataFrame(rows, columns=columns)


def load_memory(input, chat_state):
    # print("chat_state:", chat_state.memory)
    memory_vars = chat_state.memory.load_memory_variables({})
    memory_vars["chat_history"] = pairwise_chat_history_to_msg_list(chat_state.chat_history)
    # print("chat_history:", memory_vars["chat_history"])
    # memory_vars.get("chat_history", [])
    return memory_vars.get("chat_history", [])


def df_filter(title, addr):
    df_tmp = df[(df['title'] == title) & (df['ADDR'] == addr)]
    id = df_tmp['id'].iloc[0]
    id_url = f"https://m.place.naver.com/restaurant/{id}/home?entry=plt&reviewSort=recent"
    booking = df_tmp["booking"].iloc[0]
    img = df_tmp['img_url'].iloc[0]
    menu_tags = df_tmp['menu_tags'].iloc[0]
    feature_tags = df_tmp['feature_tags'].iloc[0]
    review = df_tmp['review'].iloc[0]
    revisit = df_tmp['revisit'].iloc[0]
    reservation = df_tmp['reservation'].iloc[0]
    companion = df_tmp['companion'].iloc[0]
    waiting_time = df_tmp['waiting_time'].iloc[0]
    review_count = df_tmp['v_review_cnt'].iloc[0]
    return id_url, booking, img, menu_tags, feature_tags, review, revisit, reservation, companion, waiting_time, review_count

def tags2dict(input_str):
    # 문자열을 리스트로 변환
    items = eval(input_str)

    # 딕셔너리 생성
    result_dict = {}
    for item in items[1:]:  # '특징'을 제외하고 처리
        key, value = item.split('::')
        result_dict[key] = int(value.replace(',', ''))  # 쉼표 제거 후 정수로 변환

    # 숫자가 큰 순서대로 정렬하여 상위 5개 추출
    top_5 = dict(sorted(result_dict.items(), key=lambda x: x[1], reverse=True)[:5])
    return top_5

def display_store_info(id_url, booking, img, menu_tags, feature_tags, review, revisit, reservation, companion, waiting_time, review_count):
    content = "<div style='font-family: sans-serif; padding: 10px;'>"    
    
    # if img and img.strip():
    #     content += f"<p style='margin-bottom: 0;'><b>📸 점포 사진 보기:</b></p>\n"
    #     content += f"<img src='{img}' alt='Store Image' style='width: 100%; max-width: 500px; max-height: 200px; object-fit: cover; border-radius: 10px;'>\n"
    
    if id_url and id_url.strip():
        content += f"<p style='margin-top: 0;'><b>🔗 점포 바로 가기:</b> <a href='{id_url}' style='text-decoration: none; color: #007bff;'>클릭하세요</a></p>\n"
    
    if booking and booking.strip():
        content += f"<p><b>📅 바로 예약하기:</b> <a href='{booking}' style='text-decoration: none; color: #007bff;'>여기를 클릭</a></p>\n"
    
    if review_count:
        content += f"<p><b>🔢 리뷰 수:</b> {review_count} 개</p>\n"
    
    if menu_tags and len(menu_tags) > 3:
        content += "<p style='margin-bottom: 0;'><b>🍴 인기 메뉴 (Top 5):</b></p>\n"
        content += "<div style='display: flex; flex-wrap: wrap; gap: 10px; margin-top: 0;'>"
        tag_dict = tags2dict(menu_tags)
        for key, value in tag_dict.items():
            content += f"<div style='background-color: #ffedda; border-radius: 10px; padding: 10px; min-width: 100px; text-align: center;'>"
            content += f"<b>{key}</b><br><span style='color: #ff5722;'>{value}회 언급</span>"
            content += "</div>"
        content += "</div>\n"
        
    if feature_tags and len(feature_tags) > 3:
        content += "<p style='margin-bottom: 0; margin-top: 20px;'><b>🌟 이곳의 매력 포인트 (Top 5):</b></p>\n"
        content += "<div style='display: flex; flex-wrap: wrap; gap: 10px; margin-top: 0;'>"
        tag_dict = tags2dict(feature_tags)
        for key, value in tag_dict.items():
            content += f"<div style='background-color: #ffe4f5; border-radius: 10px; padding: 10px; min-width: 100px; text-align: center;'>"
            content += f"<b>{key}</b><br><span style='color: #e91e63;'>{value}회 언급</span>"
            content += "</div>"
        content += "</div>"

    if review and review.strip():
        content += f"<p style='margin-top: 20px;'><b>💬 솔직 리뷰:</b> {review}</p>\n"
    
    if revisit and revisit.strip():
        content += f"<p><b>🔄 다시 방문할까?</b> {'예! 꼭 또 가고 싶어요!!' if '매우 높음' in revisit else '예, 재방문 의사 있어요!' if '높음' in revisit else '음, 생각중...'}</p>\n"
    
    if reservation and reservation.strip():
        content += f"<p><b>📞 예약 필요해?</b> {'예, 필수!' if '높음' in reservation else '아니요, 대부분은 예약 없이 방문했어요!'}</p>\n"
    
    if waiting_time and waiting_time.strip():
        content += f"<p><b>⏰ 얼마나 기다려야 하나요?</b> {waiting_time}</p>\n"
    
    if companion and companion.strip():
        content += f"<p><b>👥 누구랑 가면 좋을까?</b> {companion}</p>\n"
    
    content += "</div>"
    return content

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
        else: 
            pass 
    
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