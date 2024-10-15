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
    result = pd.read_sql(select_content, con=mysql_uri)
    return result

def sql_based_recommendation(result, df):
    result = extract_sql_query(result.content)
    rec = df[df["MCT_NM"].isin(result["MCT_NM"])][[
        "MCT_NM", "MCT_TYPE", "ADDR", "booking", "react1", "react2", "react3", "react4", "react5"
    ]].head()
    return {
        "recommendation": rec,
    }