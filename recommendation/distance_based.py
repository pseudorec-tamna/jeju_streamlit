import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import requests
import os
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough

import sys
sys.path.append(os.path.abspath(os.path.join('..')))
from recommendation.utils import json_format
from recommendation.prompt import address_extract_prompt

from dotenv import load_dotenv
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser

def load_memory(input):
    global memory
    memory_vars = memory.load_memory_variables({})
    return memory_vars.get("chat_history", [])

# 1. 제주상회의 주소를 좌표로 변환
def get_coordinates_by_nominatim(address):
    """
    jeju_sanghoe_address = "서울 관악구 관악로12길 108 지하1층"
    jeju_sanghoe_coords = get_coordinates(jeju_sanghoe_address)
    print(jeju_sanghoe_coords)
    """
    n = 0
    geolocator = Nominatim(user_agent="my_agent")
    location = geolocator.geocode(address)
    while (location is None):
        address = ' '.join(address.split(" ")[:-1])
        location = geolocator.geocode(address)
        n += 1 
        if n > 3: break
    return (location.longitude, location.latitude)

# 카카오 주소 추출 
import requests
def get_keyword(query):
    # https://dapi.kakao.com/v2/local/search/keyword.${FORMAT}
    api_key = os.getenv("KAKAO_API_KEY")  # 실제 Kakao API 키로 교체해야 함

    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {api_key}"}

    params = {
        "query": query
    }
    response = requests.get(url, headers=headers, params=params).json()
    return response


# 2. 카카오 좌표 변환 
import requests

def get_coordinates(address):
    url = f"https://dapi.kakao.com/v2/local/search/address.json?query={address}"
    kakao_key = os.getenv("KAKAO_API_KEY") 

    response = requests.get(url, headers={"Authorization":f"KakaoAK {kakao_key}"})
    
    if response.status_code == 200:
        result = response.json()
        if result["documents"]:
            x = result["documents"][0]["x"] # long
            y = result["documents"][0]["y"]
            return x, y
    
    print(f"Run: get_coordinates_by_nominatim")
    x, y = get_coordinates_by_nominatim(address)
    return x, y

# 3. Odsay API 호출 
import requests
import urllib.parse

# 발급받은 API KEY

def find_path(start_coords, end_coords):
    api_key = os.getenv("ODSAY_API_KEY")
    # ODsay API URL 정보
    url_info = (
        "https://api.odsay.com/v1/api/searchPubTransPathT"
        f"?SY={start_coords[1]}"  # 잠실역 # lat 
        f"&SX={start_coords[0]}" # long
        f"&EY={end_coords[1]}"  # 낙성대역
        f"&EX={end_coords[0]}"
        f"&apiKey={urllib.parse.quote(api_key)}"
    )

    # GET 요청 보내기
    response = requests.get(url_info)

    # 응답 확인
    # if response.status_code == 200:
    #     print(response.json())  # JSON 형식으로 응답 출력
    # else:
    #     print(f"Error: {response.status_code}, {response.text}")
    return response.json()

def calculate_distances(coords, df):
    x, y = coords
    distances = []
    for index, row in df.iterrows():
        coord1 = (y, x)  # (위도, 경도) 형식
        coord2 = (row['lat'], row['long'])
        distance = geodesic(coord1, coord2).km
        distances.append(distance)
    return distances

def recommend_restaurant_by_distance(coords, df):
    tmp = df.copy()
    tmp['distance'] = calculate_distances(coords, df)

    # 2km 이내 추출
    within_km = tmp[tmp['distance'] <= 2]
    if within_km.shape[0] == 0:
        within_km = tmp[tmp['distance'] <= 5]
    return within_km

def region_detection(question):
    import os 
    import google.generativeai as genai
    from langchain_google_genai import ChatGoogleGenerativeAI

    load_dotenv()

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
    prompt = ChatPromptTemplate.from_template(
        address_extract_prompt
    )

    chain = prompt | llm | StrOutputParser()

    response = chain.invoke({"user_question": question})
    response = json_format(response)["response_type"]
    return response

def distance_based_recommendation(question, df):
    region = region_detection(question)
    response = get_keyword(region)
    print(
        "region:", region,
        "response:", response
    )
    # 2. 추출된 장소의 좌표를 추출 (long, lat)
    try:
        _region = response["meta"]["same_name"]["selected_region"] + ' ' + response["meta"]["same_name"]["keyword"]
        coords = get_coordinates(_region)
    except:
        _region = response["meta"]["same_name"]["selected_region"]
        coords = get_coordinates(_region)
    print(
        "Final Region:", _region,
        "coords:", coords
    )
    # 3. 모든 맛집들의 좌표와 거리 계산
    rec = recommend_restaurant_by_distance(coords, df).reset_index(drop=True)
    rec = rec.loc[0]
    print(
        "Recommendation Result:", rec
    )
    total_minutes = find_path(start_coords=coords, end_coords=(rec.long, rec.lat))["result"]["path"][0]["info"]["totalTime"]
    distance_info = {
        "대중교통": str(total_minutes) + "분",
    }
    return {
        "recommendation": rec,
        "distance_info": distance_info
    }

def get_coordinates_by_question(question):
    region = region_detection(question)
    response = get_keyword(region)
    print(
        "region:", region,
        "response:", response
    )
    # 2. 추출된 장소의 좌표를 추출 (long, lat)
    try:
        _region = response["meta"]["same_name"]["selected_region"] + ' ' + response["meta"]["same_name"]["keyword"]
        coords = get_coordinates(_region)
    except:
        _region = response["meta"]["same_name"]["selected_region"]
        coords = get_coordinates(_region)
    return coords

def coordinates_based_recommendation(coords, df):

    # 3. 모든 맛집들의 좌표와 거리 계산
    tmp = df.copy()
    tmp = tmp[(tmp["long"].notnull()) & (tmp["lat"].notnull())]
    rec = recommend_restaurant_by_distance(coords, tmp).reset_index(drop=True)
    rec = rec[[
            "MCT_NM", "MCT_TYPE", "ADDR", "booking", "react1", "react2", "react3", "react4", "react5"
        ]].head()
    # print(
    #     "Recommendation Result:", rec
    # )
    # total_minutes = find_path(start_coords=coords, end_coords=(rec.long, rec.lat))["result"]["path"][0]["info"]["totalTime"]
    # distance_info = {
    #     "대중교통": str(total_minutes) + "분",
    # }
    return {
        "recommendation": rec,
    #     "distance_info": distance_info
    }