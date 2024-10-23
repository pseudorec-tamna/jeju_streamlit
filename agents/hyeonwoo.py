
import pandas as pd
import google.generativeai as genai
import os
import streamlit as st
from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from utils.chat_state import ChatState
from utils.prompts import chat_prompt_template, recommendation_prompt_template, recommendation_sql_prompt_template, item_search_prompt_template, explanation_template, multi_turn_template, recommendation_keyword_prompt_template

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
from recommendation.context_based import context_based_recommendation

from utils.client import MysqlClient
# from tamla import load_memory
from utils.lang_utils import pairwise_chat_history_to_msg_list
import numpy as np
from sentence_transformers import SentenceTransformer
from langchain_community.vectorstores import Chroma
from langchain.schema import Document

from langchain_community.embeddings.huggingface import HuggingFaceEmbeddings


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

query = f"select * from tamdb.detailed_info_1"
mysql.cursor.execute(query)
rows = mysql.cursor.fetchall()
columns = [i[0] for i in mysql.cursor.description]  # 컬럼 이름 가져오기
df = pd.DataFrame(rows, columns=columns)
df['ADDR_detail'] = df['ADDR'].map(lambda x: ' '.join(x.split(' ')[1:3]))
# df = df.merge(meta_info[["MCT_NM", "ADDR", "MCT_TYPE"]], how="left", on=["MCT_NM","ADDR"])


query = f"select * from tamdb.attraction_info"
mysql.cursor.execute(query)
rows = mysql.cursor.fetchall()
columns = [i[0] for i in mysql.cursor.description]  # 컬럼 이름 가져오기
df_refer = pd.DataFrame(rows, columns=columns)

path_visit_additional_info = './data/poi_df.csv' # 방문이력 데이터에 대한 id 크롤링 따로 진행
path_transition_matrix = './data/transition_matrix.csv'

transition_matrix_df = pd.read_csv(path_transition_matrix)
visit_poi_df = pd.read_csv(path_visit_additional_info)

documents = []
for row in df.iterrows():
  document = Document(
      page_content=f"""name:{row[1]['MCT_NM']}, 
      review_summary:{row[1]['review']},
      full_location:{row[1]['ADDR']}, 
      location:{row[1]['ADDR_detail']}, 
      average_score:{row[1]['average_score']}, 
      average_price:{row[1]['mean_price']},
      payment_method:{row[1]['payment']}, 
      review_counts: {row[1]['v_review_cnt']},
      menu_info:{row[1]['menu_tags']}, 
      feature_info:{row[1]['feature_tags']},
      revisit_info:{row[1]['revisit']},
      reservation_info:{row[1]['reservation']},
      companion_info:{row[1]['companion']},
      waiting_info:{row[1]['waiting_time']},
      type: {row[1]['MCT_TYPE']}
      """,
      metadata={
        "name":row[1]['MCT_NM'], 
                "review_summary":row[1]['review'],
                "full_location":row[1]['ADDR'],
                "location":row[1]['ADDR_detail'], 
                "average_score":row[1]['average_score'], 
                "average_price":row[1]['mean_price'],
                "payment_method":row[1]['payment'], 
                "review_counts": row[1]['v_review_cnt'],
                "menu_info":row[1]['menu_tags'], 
                "feature_info":row[1]['feature_tags'],
                "revisit_info":row[1]['revisit'],
                "reservation_info":row[1]['reservation'],
                "companion_info":row[1]['companion'],
                "waiting_info":row[1]['waiting_time'],
                "type": row[1]['MCT_TYPE']
      }
  )
  documents.append(document)

def invoke_form(doc):
    content = f"""
<이름>{doc.metadata['name']}<이름/>, 
<한줄평>:{doc.metadata['review_summary']}<한줄평/>,
      <지역>:{doc.metadata['location']}<지역/>, 
      <평점>:{doc.metadata['average_score']}<평점/>, 
      <평균가격>:{doc.metadata['average_price']}<평균가격/>,
      <지불방법>:{doc.metadata['payment_method']}<지불방법/>, 
      <리뷰수>: {doc.metadata['review_counts']}<리뷰수/>,
      <메뉴정보>:{doc.metadata['menu_info']}<메뉴정보/>, 
      주차정보,
      
      <특징정보>:{doc.metadata['feature_info']}<특징정보/>,
      <재방문정보>:{doc.metadata['revisit_info']}<재방문정보/>,
      <예약정보>:{doc.metadata['reservation_info']}<예약정보/>,
      <동행정보>:{doc.metadata['companion_info']}<동행정보/>,
      <웨이팅정보>:{doc.metadata['waiting_info']}<웨이팅정보/>,
      <업종>: {doc.metadata['type']}<업종/>
    """
    return content
# name:{row[1]['MCT_NM']}, 
#       review_summary:{row[1]['review']},
#       location:{row[1]['ADDR_detail']}, 
#       average_score:{row[1]['average_score']}, 
#       average_price:{row[1]['mean_price']},
#       payment_method:{row[1]['payment']}, 
#       review_counts: {row[1]['v_review_cnt']},
#       menu_info:{row[1]['menu_tags']}, 
#       feature_info:{row[1]['feature_tags']},
#       revisit_info:{row[1]['revisit']},
#       reservation_info:{row[1]['reservation']},
#       companion_info:{row[1]['companion']},
#       waiting_info:{row[1]['waiting_time']},
#       type: {row[1]['MCT_TYPE']}

#     content = f"""
# <이름>{doc.metadata['MCT_NM']}<이름/>, 
# <한줄평>:{doc.metadata['review']}<한줄평/>,
#       <주소>:{doc.metadata['ADDR_detail']}<주소/>, 
#       <평점>:{doc.metadata['average_score']}<평점/>, 
#       <평균가격>:{doc.metadata['mean_price']}<평균가격/>,
#       <지불방법>:{doc.metadata['payment']}<지불방법/>, 
#       <리뷰수>: {doc.metadata['v_review_cnt']}<리뷰수/>,
#       <메뉴정보>:{doc.metadata['menu_tags']}<메뉴정보/>, 
#       <특징정보>:{doc.metadata['feature_tags']}<특징정보/>,
#       <재방문정보>:{doc.metadata['revisit']}<재방문정보/>,
#       <예약정보>:{doc.metadata['reservation']}<예약정보/>,
#       <동행정보>:{doc.metadata['companion']}<동행정보/>,
#       <웨이팅정보>:{doc.metadata['waiting_time']}<웨이팅정보/>,
#       <업종>: {doc.metadata['MCT_TYPE']}<업종/>
#     """

def format_docs(docs):

    return "\n\n".join(invoke_form(doc) for doc in docs[0:1])
# # 정보 없는 가게 모두 제거
# df['title'].replace('', np.nan, inplace=True)
# df= df.dropna(subset='title')




# Embedding 모델 불러오기 - 개별 환경에 맞는 device로 설정
model_name = "upskyy/bge-m3-Korean"
model_kwargs = {
    # "device": "cuda"
    "device": "mps"
    # "device": "cpu"
}
encode_kwargs = {"normalize_embeddings": True}
hugging_embeddings = HuggingFaceEmbeddings(
    model_name=model_name,
    model_kwargs=model_kwargs,
    encode_kwargs=encode_kwargs,)

# hugging_vectorstore = Chroma.from_documents(
#     documents=documents,
#     embedding=hugging_embeddings,
#     persist_directory="./chroma_db"          # Save the embeddings at the first time
# )
hugging_vectorstore = Chroma(persist_directory="./chroma_db6", embedding_function=hugging_embeddings)        # Load the embeddings
hugging_retriever = hugging_vectorstore.as_retriever()


# print('렛츠고ㅇ', hugging_retriever.invoke('중문'))

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
    print(f"chat_state.info_menuplace: {chat_state.info_menuplace}")
    menuplace = chat_state.info_menuplace
    location = chat_state.info_location
    keyword = chat_state.info_keyword
    business_type = chat_state.info_business_type


    response = sub_task_detection(chat_state.message, location, menuplace, keyword)


    response_type = json_format(response)["response_type"]
    print(f"답변 타입:{response_type}")
    print('답변', json_format(response))
    if response_type == "Chat":
        chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | chat_prompt_template | llm | StrOutputParser()
        print(chain)
        result = chain.invoke({"question": chat_state.message})
    # elif response_type == "User Preference Elicitation":
    #     chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | chat_prompt_template | llm
    #     result = chain.invoke({"question": chat_state.message})
        
    # elif response_type == "Recommendation" or response_type == "User Preference Elicitation":
        rec = None # 변수 초기화
        print(f"추천 타입:{json_format(response)["response_type"]}")
        print(f"추천 요소:{json_format(response)["recommendation_factors"]}")
        menuplace = chat_state.info_menuplace = json_format(response)["recommendation_factors"]['menu_place']
        location = chat_state.info_location = json_format(response)["recommendation_factors"]['location']
        keyword = chat_state.info_keyword = json_format(response)["recommendation_factors"]['keyword']
        business_type = chat_state.info_business_type = json_format(response)["recommendation_factors"]['business_type']
    if json_format(response)["response_type"] == "Distance-based":
        chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | recommendation_prompt_template | llm | StrOutputParser()
        coord = get_coordinates_by_question(chat_state.message)
        st.write("정확한 주소를 지도에서 검색후에 클릭해주세요 !!")
        print("정확한 주소를 지도에서 검색후에 클릭해주세요 !!")

        # from IPython.display import IFrame
        latitude, longitude = coord  # coord에서 위도와 경도 추출
        # display(IFrame(src='http://127.0.0.1:5000', width=1200, height=600))
        st.components.v1.iframe('http://127.0.0.1:5000', width=650, height=600)
        
        while True: 
            response = requests.get('http://127.0.0.1:5000/get_coordinates')
            coordinates = response.json()
            latitude = coordinates['latitude']
            longitude = coordinates['longitude']
            
            print(latitude)
            print(longitude)
            if latitude is not None and longitude is not None:
                break
            time.sleep(5)
        
        rec = coordinates_based_recommendation((longitude, latitude), df)
        print('여기 조사', rec)
        rec = rec.reset_index()
        result = chain.invoke({"question": chat_state.message, "recommendations": rec['MCT_NM'][0]})  

        chat_state.info_menuplace = ['']
        chat_state.info_location = ''
        chat_state.info_keyword = ['']
        chat_state.info_business_type = ['']
        return {'answer': result, 'title': rec['MCT_NM'][0].to_dict(), 'address': rec['ADDR'][0].to_dict()}
    elif json_format(response)["response_type"] == "Attribute-based":
        return {'answer': 'nope', 'title':'', 'address': ''}

    elif json_format(response)["response_type"] == "Keyword-based":
        print('\n\n\n\n호출됐음\n\n\n\n')
        retrieved = df[df['ADDR_detail'].str.contains(location)]
        if len(retrieved) == 0:
            retrieved = df[df['MCT_NM'].str.contains(location)]
            if len(retrieved) == 0:
                retrieved = df_refer[df_refer['MCT_NM'].str.contains(location)]
        filtered_location = retrieved['ADDR_detail'].unique()
        filtered_business_type = business_type
        hugging_retriever = hugging_vectorstore.as_retriever(
            search_type='similarity',
            search_kwargs={
                'filter': {
                    "$or": [{"location": "제주"}] + [{"location": loc} for loc in filtered_location]+[{"busyness_type":business}for business in filtered_business_type]
                }
            }
        )
        row = []
        docs = hugging_retriever.invoke(chat_state.message)
        for doc in docs:
            row.append(doc.metadata)
        rec = pd.DataFrame(row).reset_index()
        print('키워드 추천 문서:', rec.iloc[0].to_dict())
        chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state))|  recommendation_keyword_prompt_template | llm | StrOutputParser()
        result = chain.invoke({"question": chat_state.message, "recommendations": rec.iloc[0].to_dict()})
        
        chat_state.info_menuplace = ['']
        chat_state.info_location = ''
        chat_state.info_keyword = ['']
        chat_state.info_business_type = ['']
        return {'answer': result, 'title': rec.iloc[0]['name'], 'address': rec.iloc[0]['full_location']}
    elif json_format(response)["response_type"] == "Multi-turn":
        chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | multi_turn_template | llm | StrOutputParser()
        print(f"location:{location}\nmenu_place:{menuplace}\nkeyword:{keyword}")
        result = chain.invoke({"question": chat_state.message, "menuplace": menuplace, "location": location, "keyword":keyword})
        return {'answer': result, 'title': '', 'address': ''}
    else: 
        pass 
        
        # 수정 필요 사항
        # 추천 기능별 rec 파일 규격 통일
        # docs 에 id 값 추가하고 rec 규격에 맞게 rec 파일 추출하기
        # next_rec을 결과로 출력할 수 있게 프롬프트 또는 response return 값 수정(?)
        # - TOP1 결과에 대해서만 제공, next_rec 값이 None인 경우도 있음 (방문이력X)
    next_rec = None
    if isinstance(rec, pd.DataFrame):
        id_t = df[df.MCT_NM==rec.iloc[0].MCT_NM].id.values[0]
        if id_t in transition_matrix_df.index:
            next_rec = context_based_recommendation(id_t, transition_matrix_df, visit_poi_df)
    print(f'--------------\n\nnextrec:{next_rec}\n\n\n--------------')
        
    # elif response_type == "Item Detail Search":
    #     # SQL 문으로 검색 가능하도록 

    #     chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | item_search_prompt_template | llm | StrOutputParser()
    #     item_info = df.loc[df["MCT_NM"] == str(chat_state.message)].reset_index(drop=True)
    #     print("item_info:", item_info)
    #     result = chain.invoke({
    #         "question": chat_state.message,
    #         "MCT_NM": item_info["MCT_NM"],
    #         "ADDR": item_info["ADDR"],
    #         "tel": item_info["tel"],
    #         "booking": item_info["booking"]
    #         })
    # elif response_type == "Explanation":
    #     chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | explanation_template | llm | StrOutputParser()
    #     item_info = df.loc[df["MCT_NM"] == str(chat_state.message)].reset_index(drop=True)
    #     print("item_info:", item_info)
    #     result = chain.invoke({
    #         "question": chat_state.message,
    #         "MCT_NM": item_info["MCT_NM"],
    #         "ADDR": item_info["ADDR"],
    #         "tel": item_info["tel"],
    #         "booking": item_info["booking"]
    #         })
    # else:
    #     pass 
    print(f"답변 타입:{response_type}")
    print('여기서의 응답', result)
    response = {"answer": result}
    print('응답', response)

    return response
