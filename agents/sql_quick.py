
import pandas as pd
import google.generativeai as genai
import os
import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from utils.chat_state import ChatState
from utils.prompts import recommendation_sql_prompt_template

from langchain_core.runnables import RunnablePassthrough
from recommendation.sql_based import extract_sql_query, sql_based_recommendation
from recommendation.prompt import template_sql_prompt
from utils.client import MysqlClient
# from tamla import load_memory
from utils.lang_utils import pairwise_chat_history_to_msg_list

# df = pd.read_csv("./data/additional_info.csv", encoding='cp949')
# df = df.drop_duplicates(subset=["MCT_NM"], keep="last")
# df = df.reset_index(drop=True)

# database = pd.read_csv("./data/JEJU_MCT_DATA_v2.csv", encoding='cp949')
# meta_info = database.drop_duplicates(subset=["MCT_NM"], keep="last")
mysql = MysqlClient()

query = f"select * from tamdb.basic_info"
mysql.cursor.execute(query)
rows = mysql.cursor.fetchall()
columns = [i[0] for i in mysql.cursor.description]  # 컬럼 이름 가져오기
df_quan = pd.DataFrame(rows, columns=columns)
# df = df.merge(meta_info[["MCT_NM", "ADDR", "MCT_TYPE"]], how="left", on=["MCT_NM","ADDR"])

def load_memory(input, chat_state):
    # print("chat_state:", chat_state.memory)
    memory_vars = chat_state.memory.load_memory_variables({})
    memory_vars["chat_history"] = pairwise_chat_history_to_msg_list(chat_state.chat_history)
    # print("chat_history:", memory_vars["chat_history"])
    # memory_vars.get("chat_history", [])
    return memory_vars.get("chat_history", [])

def get_sql_chat(chat_state: ChatState):
    # Initialize the Gemini 1.5 Flash LLM
    llm = ChatGoogleGenerativeAI(
        model=chat_state.bot_settings.llm_model_name,
        google_api_key=chat_state.google_api_key
    )
    
    chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | recommendation_sql_prompt_template | llm | StrOutputParser()
    sql_prompt = ChatPromptTemplate.from_template(template_sql_prompt)
    sql_chain = sql_prompt | llm 
    output = sql_chain.invoke({"question": chat_state.message})
    rec = sql_based_recommendation(output, df_quan)

    flag = chat_state.flag
    print('attribute 응답:', rec)
    print("output:", output.content)
    result = chain.invoke({"question": chat_state.message, "recommendations": rec['recommendation'].to_dict(), "search_info": output.content, "flag":flag})

    print(f"답변 타입: 정량 모델")
    print('여기서의 응답', result)
    response = {"answer": result, 'title': rec['recommendation']['MCT_NM'].iloc[0], 'address': rec['recommendation']['ADDR'].iloc[0]}
    print('응답', response)

    return response
