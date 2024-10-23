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
    result = pd.read_sql(select_content, con=mysql_uri)
    return result

def sql_based_recommendation(result, df):
    
    result = extract_sql_query(result.content)
    # print('데이터', df[df["MCT_NM"].isin(result["MCT_NM"].values)])
    # print('결과', result)
    # print('컬럼', df.columns)

    # SQL 결과가 안나오면 비어있을 수 있음 
    if result.shape[0] >= 1:
        rec = df[df["MCT_NM"] == result["MCT_NM"].values[0]].reset_index(drop=True)
    else:
        rec = df
    print('여어이기', rec["MCT_NM"].values[0])
    return {
        "recommendation": rec,
    }