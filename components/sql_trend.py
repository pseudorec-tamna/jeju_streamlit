
import pandas as pd
import google.generativeai as genai
import os
import streamlit as st
from utils.chat_state import ChatState
from utils.client import MysqlClient

# df = pd.read_csv("./data/additional_info.csv", encoding='cp949')
# df = df.drop_duplicates(subset=["MCT_NM"], keep="last")
# df = df.reset_index(drop=True)

# database = pd.read_csv("./data/JEJU_MCT_DATA_v2.csv", encoding='cp949')
# meta_info = database.drop_duplicates(subset=["MCT_NM"], keep="last")
mysql = MysqlClient()

# SQL 쿼리를 실행하고 DataFrame으로 변환하는 함수
def run_query(query):
    mysql.cursor.execute(query)
    rows = mysql.cursor.fetchall()
    columns = [i[0] for i in mysql.cursor.description]  # 컬럼 이름 가져오기
    return pd.DataFrame(rows, columns=columns)

def df_local_sql(list_price):
    # 현지인 비중이 높은 맛집
    query_local = f"""
    SELECT di.*, bi.LOCAL_UE_CNT_RAT, bi.UE_AMT_PER_TRSN_GRP
    FROM tamdb.basic_info bi
    LEFT JOIN detailed_info_1 di 
    ON bi.MCT_NM = di.MCT_NM AND bi.ADDR = di.ADDR
    WHERE bi.YM = '202312' and di.mean_price >= {list_price[0]} and di.mean_price <= {list_price[1]}
    ORDER BY bi.LOCAL_UE_CNT_RAT DESC
    LIMIT 30;
    """
    df_local = run_query(query_local)
    return df_local

def df_male_sql(list_price):
    # 남성 비중이 높은 맛집 - 상위 30개
    query_male_high = f"""
    SELECT di.*, bi.RC_M12_MAL_CUS_CNT_RAT, bi.UE_AMT_PER_TRSN_GRP
    FROM tamdb.basic_info bi
    LEFT JOIN detailed_info_1 di 
    ON bi.MCT_NM = di.MCT_NM AND bi.ADDR = di.ADDR
    WHERE bi.YM = '202312' AND di.mean_price >= {list_price[0]} AND di.mean_price <= {list_price[1]}
    ORDER BY bi.RC_M12_MAL_CUS_CNT_RAT DESC
    LIMIT 30;
    """
    df_male_high = run_query(query_male_high)
    return df_male_high

def df_female_sql(list_price):
    # 여성 비중이 높은 맛집 - 상위 30개
    query_female_high = f"""
    SELECT di.*, bi.RC_M12_FME_CUS_CNT_RAT, bi.UE_AMT_PER_TRSN_GRP
    FROM tamdb.basic_info bi
    LEFT JOIN detailed_info_1 di 
    ON bi.MCT_NM = di.MCT_NM AND bi.ADDR = di.ADDR
    WHERE bi.YM = '202312' AND di.mean_price >= {list_price[0]} AND di.mean_price <= {list_price[1]}
    ORDER BY bi.RC_M12_FME_CUS_CNT_RAT DESC
    LIMIT 30;
    """
    df_female_high = run_query(query_female_high)
    return df_female_high

def df_age_20_sql(list_price):
    # 20대 비중이 높은 맛집 - 상위 30개
    query_age_20 = f"""
    SELECT di.*, bi.RC_M12_AGE_UND_20_CUS_CNT_RAT, bi.UE_AMT_PER_TRSN_GRP
    FROM tamdb.basic_info bi
    LEFT JOIN detailed_info_1 di 
    ON bi.MCT_NM = di.MCT_NM AND bi.ADDR = di.ADDR
    WHERE bi.YM = '202312' AND di.mean_price >= {list_price[0]} AND di.mean_price <= {list_price[1]}
    ORDER BY bi.RC_M12_AGE_UND_20_CUS_CNT_RAT DESC
    LIMIT 30;
    """
    df_age_20 = run_query(query_age_20)
    return df_age_20

def df_age_30_sql(list_price):
    # 30대 비중이 높은 맛집 - 상위 30개
    query_age_30 = f"""
    SELECT di.*, bi.RC_M12_AGE_30_CUS_CNT_RAT, bi.UE_AMT_PER_TRSN_GRP
    FROM tamdb.basic_info bi
    LEFT JOIN detailed_info_1 di 
    ON bi.MCT_NM = di.MCT_NM AND bi.ADDR = di.ADDR
    WHERE bi.YM = '202312' AND di.mean_price >= {list_price[0]} AND di.mean_price <= {list_price[1]}
    ORDER BY bi.RC_M12_AGE_30_CUS_CNT_RAT DESC
    LIMIT 30;
    """
    df_age_30 = run_query(query_age_30)
    return df_age_30

def df_age_40_sql(list_price):
    # 40대 비중이 높은 맛집 - 상위 30개
    query_age_40 = f"""
    SELECT di.*, bi.RC_M12_AGE_40_CUS_CNT_RAT, bi.UE_AMT_PER_TRSN_GRP
    FROM tamdb.basic_info bi
    LEFT JOIN detailed_info_1 di 
    ON bi.MCT_NM = di.MCT_NM AND bi.ADDR = di.ADDR
    WHERE bi.YM = '202312' AND di.mean_price >= {list_price[0]} AND di.mean_price <= {list_price[1]}
    ORDER BY bi.RC_M12_AGE_40_CUS_CNT_RAT DESC
    LIMIT 30;
    """
    df_age_40 = run_query(query_age_40)
    return df_age_40

def df_age_50_sql(list_price):
    # 50대 비중이 높은 맛집 - 상위 30개
    query_age_50 = f"""
    SELECT di.*, bi.RC_M12_AGE_50_CUS_CNT_RAT, bi.UE_AMT_PER_TRSN_GRP
    FROM tamdb.basic_info bi
    LEFT JOIN detailed_info_1 di 
    ON bi.MCT_NM = di.MCT_NM AND bi.ADDR = di.ADDR
    WHERE bi.YM = '202312' AND di.mean_price >= {list_price[0]} AND di.mean_price <= {list_price[1]}
    ORDER BY bi.RC_M12_AGE_50_CUS_CNT_RAT DESC
    LIMIT 30;
    """
    df_age_50 = run_query(query_age_50)
    return df_age_50

def df_age_60_sql(list_price):
    # 60대 비중이 높은 맛집 - 상위 30개
    query_age_60 = f"""
    SELECT di.*, bi.RC_M12_AGE_OVR_60_CUS_CNT_RAT, bi.UE_AMT_PER_TRSN_GRP
    FROM tamdb.basic_info bi
    LEFT JOIN detailed_info_1 di 
    ON bi.MCT_NM = di.MCT_NM AND bi.ADDR = di.ADDR
    WHERE bi.YM = '202312' AND di.mean_price >= {list_price[0]} AND di.mean_price <= {list_price[1]}
    ORDER BY bi.RC_M12_AGE_OVR_60_CUS_CNT_RAT DESC
    LIMIT 30;
    """
    df_age_60 = run_query(query_age_60)
    return df_age_60


def trend_df(chat_state: ChatState):
    flag_trend = chat_state.flag_trend
    price_range = chat_state.price_range
    
    # 각 flag_trend 값에 따라 적절한 SQL 함수 호출
    if flag_trend == 'male':
        df = df_male_sql(price_range)
    elif flag_trend == 'female':
        df = df_female_sql(price_range)
    elif flag_trend == '20':
        df = df_age_20_sql(price_range)
    elif flag_trend == '30':
        df = df_age_30_sql(price_range)
    elif flag_trend == '40':
        df = df_age_40_sql(price_range)
    elif flag_trend == '50':
        df = df_age_50_sql(price_range)
    elif flag_trend == '60':
        df = df_age_60_sql(price_range)
    else:
        df = df_local_sql(price_range)

    return df