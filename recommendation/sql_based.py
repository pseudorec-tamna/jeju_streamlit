import re
import pandas as pd
import os 
from dotenv import load_dotenv
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
USERNAME = os.getenv("DB_USER")
PASSWORD = os.getenv("DB_PASSWORD")
DATABASE_SCHEMA = os.getenv("DB_NAME")
mysql_uri = f"mysql+pymysql://{USERNAME}:{PASSWORD}@{DB_HOST}:{DB_PORT}/{DATABASE_SCHEMA}"
import re

regions = [
    '용담이동', '애월읍', '색달동', '한림읍', '노형동', '일도일동', '아라일동', '연동', '토평동',
    '대포동', '삼도이동', '서귀동', '일도이동', '대정읍', '한경면', '조천읍', '이도이동', '내도동',
    '호근동', '서홍동', '성산읍', '건입동', '표선면', '법환동', '외도일동', '삼도일동', '도두일동',
    '구좌읍', '하예동', '이도일동', '동홍동', '안덕면', '도남동', '용담삼동', '아라이동', '서호동',
    '삼양이동', '중문동', '남원읍', '강정동', '해안동', '오라삼동', '도두이동', '화북일동', '외도이동',
    '신효동', '우도면', '용담일동', '화북이동', '오라이동', '보목동', '하효동', '봉개동', '오라일동',
    '도련일동', '월평동', '회천동', '도련이동', '삼양일동', '상예동', '이호일동', '도평동', '오등동',
    '이호이동', '상효동', '도순동', '삼양삼동', '영평동', '하원동', '회수동', '추자면', '이도2동',
    '영남동'
]

def add_percent_around_region(text, regions):
    for region in regions:
        if region in text:
            # 해당 지역명을 %로 감싸서 새로운 문자열 생성
            text = text.replace(region, f" {region}")
    return text



def extract_sql_query(result):
    import re

    pattern = r"(SELECT[\s\S]*?;)"
    match = re.search(pattern, result, re.IGNORECASE)

    if match:
        select_content = match.group(1).strip()
    else:
        print("SELECT 문을 찾을 수 없습니다.")

    from sqlalchemy import text
    
    select_content = text(select_content.encode('utf-8').decode('utf-8'))
    # print(f"쿼리: {select_content}")
    print('쿼리', select_content)
    result = pd.read_sql(select_content, con=mysql_uri)
    return result

def sql_based_recommendation(result, df):
    
    result_df = extract_sql_query(result.content)
    tmp = ""
    
    # SQL 결과가 안나오면 비어있을 수 있음 
    if result_df.shape[0] >= 1:
        rec = df[df["MCT_NM"].isin(list(result_df["MCT_NM"].unique()))].reset_index(drop=True)
    else:
        result_df = extract_sql_query(add_percent_around_region(result.content, regions))
        if result_df.shape[0] >= 1:
            rec = df[df["MCT_NM"].isin(list(result_df["MCT_NM"].unique()))].reset_index(drop=True)
        else:    
            rec = df[df.UE_CNT_GRP == "1_상위 10% 이하"].sample(20)
            tmp = "* 아래 결과는 예시일 뿐 실제 데이터는 검색되지 않았습니다. 해당 질문에 맞는 데이터가 존재하지 않습니다."
    print('여어이기', len(rec))
    return {
        "recommendation": rec,
        "tmp":tmp
    }