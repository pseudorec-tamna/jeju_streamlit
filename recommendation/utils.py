import json
import ast
import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import requests
from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from recommendation.prompt import sub_task_detection_prompt, address_extract_prompt, sql_task_detection_prompt
import google.generativeai as genai
from dotenv import load_dotenv
from utils.prepare import GEMINI_API_KEY
def json_format(response):
    response = response.replace("json", '')
    response = response.replace("```", '').strip()
    response = ast.literal_eval(response)
    return response

def get_coordinates(address):
    """
    jeju_sanghoe_address = "서울 관악구 관악로12길 108 지하1층"
    jeju_sanghoe_coords = get_coordinates(jeju_sanghoe_address)
    나인온스(낙성대점), 108, 관악로12길, 낙성대동, 관악구, 서울특별시, 08789, 대한민국 서울 관악구 관악로12길 108
    """
    geolocator = Nominatim(user_agent="my_agent")
    location = geolocator.geocode(address)
    return (location.latitude, location.longitude)

def calculate_distance(coord1, coord2):
    """
    coord1 = (37.5665, 126.978)  # 서울
    coord2 = (35.1796, 129.0756)  # 부산

    # 거리 계산
    distance = calculate_distance(coord1, coord2)
    print(f"서울과 부산의 거리: {distance:.2f} km")
    """
    return geodesic(coord1, coord2).km

def sub_task_detection(question, location, menuplace, keyword, original_question):
    import os 
    load_dotenv()

    # genai.configure(api_key="AIzaSyBs54U6aYVwaVVe4KKnPFzc-eQQDMkLIcA")
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=GEMINI_API_KEY)
    prompt = ChatPromptTemplate.from_template(
        sub_task_detection_prompt
    )
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({"user_question": question, "location":location, "menuplace": menuplace, "keyword": keyword, "original_quesetion": original_question})

    """
    5개의 Type 중 하나를 선택 
    User Preference Elicitation, Recommendation, Explanation, Item Detail Search, Chat

    만약 Recommendation이라면 추가적으로 추천 Type을 결정 
    Distance-based, Attribute-based, Content-based
    """
    # response_type = json_format(response)["response_type"]
    return response
def sql_task_detection(question):
    import os 
    load_dotenv()
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=GEMINI_API_KEY)
    prompt = ChatPromptTemplate.from_template(
        sql_task_detection_prompt
    )
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({"user_question": question})

    return response