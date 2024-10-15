from datetime import datetime

from components.llm import get_prompt_llm_chain
from utils.chat_state import ChatState
from utils.prompts import CHAT_GREETING_PROMPT
from utils.prepare import WEATHER_KEY
from datetime import datetime, timedelta
import requests
import json  
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain


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

def get_greeting_chat_chain(
    chat_state: ChatState,
    prompt_qa=CHAT_GREETING_PROMPT,
):
    flag = chat_state.flag

    # Initialize the Gemini 1.5 Flash LLM
    llm = ChatGoogleGenerativeAI(
        model=chat_state.bot_settings.llm_model_name,
        google_api_key=chat_state.google_api_key
    )

    chain = LLMChain(llm=llm, prompt=prompt_qa)

    # 현재 제주 날씨 API 
    weather_dict = jeju_weather_dict()

    # Ensure the message is passed; if not, provide a default
    message = ""

    # LLM execution and get the response
    answer = chain.run({
        "date": weather_dict['date'],
        "time": weather_dict['time'],
        "temperature": float(weather_dict['temperature'][:-1]),
        "weather_condition": weather_dict['sky_condition'],
        "flag": flag,
        "chat_history": chat_state.chat_history,
        "message": message,
    })

    return answer

