
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

df = pd.read_csv("./data/additional_info.csv", encoding='cp949')
df = df.drop_duplicates(subset=["MCT_NM"], keep="last")
df = df.reset_index(drop=True)

database = pd.read_csv("./data/JEJU_MCT_DATA_v2.csv", encoding='cp949')
meta_info = database.drop_duplicates(subset=["MCT_NM"], keep="last")
df = df.merge(meta_info[["MCT_NM", "MCT_TYPE"]], how="left", on="MCT_NM")

def load_memory(input, chat_state):
    # print("chat_state:", chat_state.memory)
    memory_vars = chat_state.memory.load_memory_variables({})
    memory_vars["chat_history"] = pairwise_chat_history_to_msg_list(chat_state.chat_history)
    # print("chat_history:", memory_vars["chat_history"])
    # memory_vars.get("chat_history", [])
    return memory_vars.get("chat_history", [])

def get_hw_response(chat_state: ChatState):
    # Initialize the Gemini 1.5 Flash LLM
    llm = ChatGoogleGenerativeAI(
        model=chat_state.bot_settings.llm_model_name,
        google_api_key=chat_state.google_api_key
    )

    response = sub_task_detection(chat_state.message)
    response_type = json_format(response)["response_type"]

    if response_type == "Chat":
        chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | chat_prompt_template | llm
        result = chain.invoke({"question": chat_state.message})

    elif response_type == "Recommendation":
        
        if json_format(response)["recommendation_type"] == "Distance-based":
            chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | recommendation_prompt_template | llm
            coord = get_coordinates_by_question(chat_state.message)
            print("정확한 주소를 지도에서 검색후에 클릭해주세요 !!")

            from IPython.display import IFrame
            latitude, longitude = coord  # coord에서 위도와 경도 추출
            display(IFrame(src='http://127.0.0.1:5000', width=1200, height=600))
            
            while True: 
                response = requests.get('http://127.0.0.1:5000/get_coordinates')
                coordinates = response.json()
                latitude = coordinates['latitude']
                longitude = coordinates['longitude']
                if latitude is not None and longitude is not None:
                    break
                time.sleep(5)
            
            rec = coordinates_based_recommendation((longitude, latitude), df)
            result = chain.invoke({"question": chat_state.message, "recommendations": rec})  
        elif json_format(response)["recommendation_type"] == "Attribute-based":
            chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | recommendation_sql_prompt_template | llm
            sql_prompt = ChatPromptTemplate.from_template(template_sql_prompt)
            sql_chain = sql_prompt | llm
            output = sql_chain.invoke({"question": chat_state.message})            
            rec = sql_based_recommendation(output, df)
            result = chain.invoke({"question": chat_state.message, "recommendations": rec, "search_info": output.content})  
        else: 
            pass 
              
    elif response_type == "Item Detail Search":
        # SQL 문으로 검색 가능하도록 

        chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | item_search_prompt_template | llm
        item_info = df.loc[df["MCT_NM"] == str(chat_state.message)].reset_index(drop=True)
        print("item_info:", item_info)
        result = chain.invoke({
            "question": chat_state.message,
            "MCT_NM": item_info["MCT_NM"],
            "ADDR": item_info["ADDR"],
            "tel": item_info["tel"],
            "booking": item_info["booking"]
            })
    else: 
        pass 
    response = {"answer": result.content}
    return response