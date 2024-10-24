
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


def df_filter(mct_nm, addr):
    df_tmp = df[(df['MCT_NM'] == mct_nm) & (df['ADDR'] == addr)]
    
    if df_tmp.empty:
        df_tmp = df[(df['MCT_NM'].str.contains(mct_nm, na=False)) & (df['ADDR'] == addr)]

    # 데이터가 있는지 확인
    if df_tmp.empty:
        return None
    
    # 안전하게 값을 가져오기 위해 get 메서드 사용
    def safe_get(series, default=None):
        return series.iloc[0] if not series.empty else default

    id = safe_get(df_tmp['id'])
    if id is None:
        return None  # id가 없으면 None 반환

    id_url = f"https://m.place.naver.com/restaurant/{id}/home?entry=plt&reviewSort=recent"
    booking = safe_get(df_tmp['booking'], default="")
    img = safe_get(df_tmp['img_url'], default="")
    menu_tags = safe_get(df_tmp['menu_tags'], default="")
    feature_tags = safe_get(df_tmp['feature_tags'], default="")
    review = safe_get(df_tmp['review'], default="")
    revisit = safe_get(df_tmp['revisit'], default="")
    reservation = safe_get(df_tmp['reservation'], default="")
    companion = safe_get(df_tmp['companion'], default="")
    waiting_time = safe_get(df_tmp['waiting_time'], default="")
    review_count = safe_get(df_tmp['v_review_cnt'], default=0)

    return id_url, booking, img, menu_tags, feature_tags, review, revisit, reservation, companion, waiting_time, review_count

def tags2dict(input_str):
    # 문자열을 리스트로 변환
    items = eval(input_str)
    
    # 딕셔너리 생성
    result_dict = {}
    for item in items[1:]:  # '특징'을 제외하고 처리
        # '::'로 분리하고, 분리된 값의 개수를 확인
        split_item = item.split('::')
        
        if len(split_item) == 2:  # 예상된 값이 두 개인 경우에만 처리
            key, value = split_item
            result_dict[key] = int(value.replace(',', ''))  # 쉼표 제거 후 정수로 변환
        else:
            # '::'가 없는 경우의 처리 (예: '특징' 등)
            top_5 = None
            # print(f"Invalid item format: {item}")
            
    # 숫자가 큰 순서대로 정렬하여 상위 5개 추출
    top_5 = dict(sorted(result_dict.items(), key=lambda x: x[1], reverse=True)[:5])

    return top_5

def display_store_info(id_url, booking, img, menu_tags, feature_tags, review, revisit, reservation, companion, waiting_time, review_count):
    content = "<div style='font-family: sans-serif; padding: 10px;'>"   
    menu_tags = menu_tags.strip()
    feature_tags = feature_tags.strip()
    
    # if img and img.strip():
    #     content += f"<p style='margin-bottom: 0;'><b>📸 점포 사진 보기:</b></p>\n"
    #     content += f"<img src='{img}' alt='Store Image' style='width: 100%; max-width: 500px; max-height: 200px; object-fit: cover; border-radius: 10px;'>\n"
    
    if id_url and id_url.strip():
        content += f"<p style='margin-top: 0;'><b>🔗 점포 바로 가기:</b> <a href='{id_url}' style='text-decoration: none; color: #007bff;'>클릭하세요</a></p>\n"
    
    if booking and booking.strip():
        content += f"<p><b>📅 바로 예약하기:</b> <a href='{booking}' style='text-decoration: none; color: #007bff;'>여기를 클릭</a></p>\n"
    
    if review_count and str(review_count) > "0":
        content += f"<p><b>🔢 리뷰 수:</b> {review_count} 개</p>\n"
    
    if menu_tags and len(menu_tags) > 5:
        content += "<p style='margin-bottom: 0;'><b>🍴 인기 메뉴 (Top 5):</b></p>\n"
        content += "<div style='display: flex; flex-wrap: wrap; gap: 10px; margin-top: 0;'>"
        tag_dict = tags2dict(menu_tags)
        if tag_dict:
            for key, value in tag_dict.items():
                content += f"<div style='background-color: #ffedda; border-radius: 10px; padding: 10px; min-width: 100px; text-align: center;'>"
                content += f"<b>{key}</b><br><span style='color: #ff5722;'>{value}회 언급</span>"
                content += "</div>"
        content += "</div>\n"
        
    if feature_tags and len(feature_tags) > 5:
        content += "<p style='margin-bottom: 0; margin-top: 20px;'><b>🌟 이곳의 매력 포인트 (Top 5):</b></p>\n"
        content += "<div style='display: flex; flex-wrap: wrap; gap: 10px; margin-top: 0;'>"
        tag_dict = tags2dict(feature_tags)
        if tag_dict:
            for key, value in tag_dict.items():
                content += f"<div style='background-color: #ffe4f5; border-radius: 10px; padding: 10px; min-width: 100px; text-align: center;'>"
                content += f"<b>{key}</b><br><span style='color: #e91e63;'>{value}회 언급</span>"
                content += "</div>"
        content += "</div>"

    if review and review.strip():
        content += f"<p style='margin-top: 20px;'><b>💬 솔직 리뷰:</b> {review}</p>\n"
    
    if revisit and revisit.strip():
        content += f"<p><b>🔄 다시 방문할까?</b> {'예! 꼭 또 가고 싶어요!!' if '매우 높음' in revisit else '예, 재방문 의사 있어요!' if '높음' in revisit else '음, 다시 방문할지는 잘 모르겠어요!'}</p>\n"
    
    if reservation and reservation.strip():
        content += f"<p><b>📞 예약 필요해?</b> {'예, 필수!' if '높음' in reservation else '아니요, 대부분은 예약 없이 방문했어요!'}</p>\n"
    
    if waiting_time and waiting_time.strip():
        content += f"<p><b>⏰ 얼마나 기다려야 하나요?</b> {waiting_time}</p>\n"
    
    if companion and companion.strip():
        content += f"<p><b>👥 누구랑 가면 좋을까?</b> {companion}</p>\n"
    
    content += "</div>"
    return content
