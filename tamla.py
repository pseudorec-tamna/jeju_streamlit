import os
from typing import Any

from langchain.chains import LLMChain
from utils.prepare import DEFAULT_OPENAI_API_KEY, WEATHER_KEY, get_logger
from utils.chat_state import ChatState
from utils.type_utils import OperationMode
from utils.prompts import (
    JUST_CHAT_PROMPT,
)
from components.llm import get_prompt_llm_chain
from utils.lang_utils import pairwise_chat_history_to_msg_list
from datetime import datetime, timedelta
import requests
import json  
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain


logger = get_logger()

default_vectorstore = None  # can move to chat_state


def date_time():
    # 현재 시간
    now = datetime.now()
    
    # 1시간 전 시간 계산
    one_hour_ago = now - timedelta(hours=1)
    
    # 1시간 전 날짜 및 시간 형식 지정 (YYYYMMDD, HH00)
    one_hour_ago_str = one_hour_ago.strftime("%Y%m%d")
    one_hour_ago_time_str = one_hour_ago.strftime("%H00")
    return one_hour_ago_str, one_hour_ago_time_str

def jeju_info(serviceKey, one_hour_ago_str, one_hour_ago_time_str):
    # parameters
    base_date = one_hour_ago_str
    base_time = one_hour_ago_time_str
    nx = '53'
    ny = '38' 
    url = f"http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtFcst?serviceKey={serviceKey}&numOfRows=60&pageNo=1&dataType=json&base_date={base_date}&base_time={base_time}&nx={nx}&ny={ny}"
    
    response = requests.get(url, verify=False)
    res = json.loads(response.text)
    
    informations = dict()
    for items in res['response']['body']['items']['item'] :
        cate = items['category']
        fcstTime = items['fcstTime']
        fcstValue = items['fcstValue']
        temp = dict()
        temp[cate] = fcstValue
        
        if fcstTime not in informations.keys() :
            informations[fcstTime] = dict()
    
        informations[fcstTime][cate] = fcstValue
    return informations 

def deg_to_dir(deg) :
    deg_code = {0 : 'N', 360 : 'N', 180 : 'S', 270 : 'W', 90 : 'E', 22.5 :'NNE',
           45 : 'NE', 67.5 : 'ENE', 112.5 : 'ESE', 135 : 'SE', 157.5 : 'SSE',
           202.5 : 'SSW', 225 : 'SW', 247.5 : 'WSW', 292.5 : 'WNW', 315 : 'NW',
           337.5 : 'NNW'}

    close_dir = ''
    min_abs = 360
    if deg not in deg_code.keys() :
        for key in deg_code.keys() :
            if abs(key - deg) < min_abs :
                min_abs = abs(key - deg)
                close_dir = deg_code[key]
    else : 
        close_dir = deg_code[deg]
    return close_dir

def parse_weather_data(informations, base_date, deg_to_dir):
    # 코드 매핑
    pyt_code = {0: '강수 없음', 1: '비', 2: '비/눈', 3: '눈', 5: '빗방울', 6: '진눈깨비', 7: '눈날림'}
    sky_code = {1: '맑음', 3: '구름많음', 4: '흐림'}

    # 날씨 정보를 저장할 리스트
    weather_data = []

    # 지역 정보
    nx = '53'
    ny = '38' 

    # 날씨 정보 처리
    for key, val in zip(informations.keys(), informations.values()):
        weather_dict = {
            "date": f"{base_date[:4]}년 {base_date[4:6]}월 {base_date[-2:]}일",
            "time": f"{key[:2]}시",
            "location": (int(nx), int(ny)),
            "sky_condition": None,
            "precipitation_type": None,
            "precipitation_amount": None,
            "temperature": None,
            "humidity": None,
            "wind_direction": None,
            "wind_speed": None
        }

        # 하늘 상태
        if 'SKY' in val and val['SKY']:
            weather_dict["sky_condition"] = sky_code.get(int(val['SKY']), None)

        # 강수 상태
        if 'PTY' in val and val['PTY']:
            weather_dict["precipitation_type"] = pyt_code.get(int(val['PTY']), None)
            if val['RN1'] != '강수없음':
                weather_dict["precipitation_amount"] = f"{val['RN1']}mm"

        # 기온
        if 'T1H' in val and val['T1H']:
            weather_dict["temperature"] = f"{float(val['T1H'])}℃"

        # 습도
        if 'REH' in val and val['REH']:
            weather_dict["humidity"] = f"{float(val['REH'])}%"

        # 풍향/풍속
        if 'VEC' in val and 'WSD' in val and val['VEC'] and val['WSD']:
            weather_dict["wind_direction"] = deg_to_dir(float(val['VEC']))
            weather_dict["wind_speed"] = f"{val['WSD']}m/s"

        # 완성된 날씨 정보를 리스트에 추가
        weather_data.append(weather_dict)
        break  # break는 테스트 목적으로 추가한 것 같으니, 필요 시 제거 가능

    return weather_data

def jeju_weather_dict():
    # 제주도 최근 날씨 정보 얻기 
    one_hour_ago_str, one_hour_ago_time_str = date_time()
    informations = jeju_info(WEATHER_KEY, one_hour_ago_str, one_hour_ago_time_str)
    weather_dict = parse_weather_data(informations, one_hour_ago_str, deg_to_dir)[0]
    return weather_dict 

# 날씨 및 음식 추천 프롬프트 생성 함수
def generate_greeting(chat_model, date, time, temperature, weather_condition, flag):
    chat_prompt = ChatPromptTemplate.from_template("""
        현재 제주도의 날씨를 기반으로 친근하고 재미있으며 약간 재치 있는 인사말을 만들어주세요.
        오늘 날짜는 {date}이고, 현재 시간은 {time}입니다. 인사말을 만들 때 연중 날짜와 시간대를 고려해주세요.
        예를 들어:
        - 만약 오늘이 12월 31일이라면, 특별한 날임을 언급하고 축하할 만한 식사를 제안하세요.
        - 만약 점심시간(오전 11시 ~ 오후 2시)이라면, 점심 메뉴를 제안하세요.
        - 만약 저녁시간(오후 5시 ~ 오후 8시)이라면, 저녁 메뉴를 제안하세요.
        - 제주도의 지역 음식인 '흑돼지', '전복죽', '고등어회', '고기국수', '딱새우', '성게 미역국', '오메기떡', '갈치조림' 등을 우선적으로 제안하되, 적절하지 않다면 일반적인 음식을 제안하세요.
        
        현재 기온({temperature}°C)과 날씨 상태({weather_condition})를 언급하세요.
        메시지를 재미있고 상황에 맞게 개인화해주세요.
        
        예시 형식:
        1.
        - 인사말: "오늘 기온은 {temperature}°C로, {weather_condition}입니다. {time}인 지금, 제주도의 유명한 흑돼지 BBQ로 멋진 저녁을 즐겨보는 건 어떨까요?"
        
        2.
        - 인사말: "현재 기온은 {temperature}°C이며, {weather_condition}입니다. 상쾌한 점심을 즐기기 딱 좋은 시간이에요. 제주식 해물구이로 하루를 즐겨보세요!"
        
        3.
        - 인사말: "오늘은 12월 31일, 특별한 날이에요! 기온은 {temperature}°C로, {weather_condition}입니다. 한 해의 마무리를 제주도의 유명한 해물탕으로 축하해보는 건 어떨까요?"
        
        4.
        - 인사말: "기온은 {temperature}°C이고, {weather_condition}입니다. 저녁시간에 약간 쌀쌀하니, 제주 갈치조림으로 몸을 녹여보세요!"
        
        5.
        - 인사말: "좋은 오후입니다! 제주도는 현재 기온 {temperature}°C에 {weather_condition}입니다. 신선한 해산물과 시원한 음료로 맛있는 점심을 즐겨보세요!"
        
        6.
        - 인사말: "오늘 제주도는 아름다운 맑은 날씨에 기온이 {temperature}°C입니다. 점심시간인 지금, 더위를 이길 수 있는 제주 냉면 한 그릇은 어떠세요?"
        
        안녕하세요는 생락하고, 톤을 친근하고 매력적으로 유지하며, 음식 제안이 세심하게 느껴지도록 해주세요. 따옴표 없이 인사말은 최대한 간단하게 {flag} 적어주세요. 
        """)
    chain = LLMChain(llm=chat_model, prompt=chat_prompt)

    # LLM 실행 및 응답 받기
    greeting = chain.run({
        "date": date,
        "time": time,
        "temperature": temperature,
        "weather_condition": weather_condition,
        "flag":flag
    })
    return greeting.strip()

def jeju_greeting(weather_dict, flag=""):
    # ChatOpenAI 모델 초기화
    chat_model = ChatOpenAI(
        model_name="gpt-4o",  # 또는 사용 가능한 최신 모델
        openai_api_key=DEFAULT_OPENAI_API_KEY,
        temperature=0.7
    )

    # 인사말 생성 실행 
    greeting = generate_greeting(chat_model, weather_dict['date'], weather_dict['time'], float(weather_dict['temperature'][:-1]),  weather_dict['sky_condition'], flag)
    return greeting

def get_bot_response(
    chat_state: ChatState,
):
    chat_chain = get_prompt_llm_chain(
        JUST_CHAT_PROMPT,
        llm_settings=chat_state.bot_settings,
        api_key=chat_state.openai_api_key,
        callbacks=chat_state.callbacks,
        stream=True,
    )
    answer = chat_chain.invoke(
        {
            "message": chat_state.message,
            "chat_history": pairwise_chat_history_to_msg_list(
                chat_state.chat_history
            ),
        }
    )
    return {"answer": answer}


if __name__ == "__main__":
    chat_history = []
    
    response = get_bot_response(
        ChatState(
            operation_mode=OperationMode.CONSOLE,
            chat_history=chat_history,
            openai_api_key=DEFAULT_OPENAI_API_KEY,
            user_id=None,  # would be set to None by default but just to be explicit
        )
    )