
import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser

from utils.chat_state import ChatState
from utils.prompts import chat_prompt_template
from agents.hyeonwoo import keyword_based
from recommendation.context_based import context_based_recommendation

from recommendation.utils import json_format
# from colorama import Fore, Style
from langchain_core.runnables import RunnablePassthrough
from recommendation.utils import sub_task_detection
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



def load_memory(input, chat_state):
    # print("chat_state:", chat_state.memory)
    memory_vars = chat_state.memory.load_memory_variables({})
    memory_vars["chat_history"] = pairwise_chat_history_to_msg_list(chat_state.chat_history)
    # print("chat_history:", memory_vars["chat_history"])
    # memory_vars.get("chat_history", [])
    return memory_vars.get("chat_history", [])

def get_keywords_chat(chat_state: ChatState):
    flag_eng = chat_state.flag_eng

    llm = ChatGoogleGenerativeAI(
        model=chat_state.bot_settings.llm_model_name,
        google_api_key=chat_state.google_api_key,
    )

    # 벡터DB 로드
    hugging_vectorstore = chat_state.vectorstore
    hugging_retriever_baseline = hugging_vectorstore.as_retriever()
    print(f"chat_state.info_menuplace: {chat_state.info_menuplace}")
    
    # 질의 분류
    response = sub_task_detection(
        chat_state.message, 
        chat_state.info_location, 
        chat_state.info_menuplace, 
        chat_state.info_keyword,
        chat_state.original_question
    )
    if response == '': # 욕설 등으로 인해서 출력이 제대로 완성되지 않은 경우 
        # 여기에 어떤 내용을 채울지에 대한 고민 
        return {'answer': '', 'title': '', 'address': '', 'next_rec': ''}

    print('여기서부터 분석 시작')

    print('------')

    # 질의 유형 
    response_type = json_format(response)["response_type"]

    # 질의 요소 
    recommendation_factors = json_format(response)["recommendation_factors"]

    # 필요 질의문 보관
    original_question = chat_state.original_question = json_format(response)["original_question"]
    
    print(f"답변 타입: {response_type}")
    print('답변', json_format(response))
    if (recommendation_factors['location'] == '제주' or recommendation_factors['location'] == '제주도') and response_type == "Keyword-based":
        recommendation_factors['location'] = ''
        response_type = "Multi-turn"
    
    for keyword in ["근처", "가까운"]: 
        if (chat_state.message.find(keyword) != -1) and (response_type != 'Multi-turn'): 
            response_type = json_format(response)["response_type"] = "Distance-based"
    
    menuplace = chat_state.info_menuplace = recommendation_factors['menu_place'] = list(set(recommendation_factors['menu_place'] + chat_state.info_menuplace))
    location = chat_state.info_location = recommendation_factors['location'] = recommendation_factors['location'] if (chat_state.info_location == '' or chat_state.info_location == recommendation_factors['location']) else chat_state.info_location + recommendation_factors['location']
    keyword = chat_state.info_keyword = recommendation_factors['keyword'] = list(set(recommendation_factors['keyword'] + chat_state.info_keyword))
    business_type = chat_state.info_business_type = recommendation_factors['business_type'] = list(set(recommendation_factors['business_type'] + chat_state.info_business_type))
    query_rewrite = chat_state.query_rewrite = recommendation_factors["query_rewrite"] 
    
    if response_type == "Chat":
        chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | chat_prompt_template | llm | StrOutputParser()
        result = chain.invoke({"question": chat_state.message, "flag_eng":flag_eng})
        rec = None # 변수 초기화
        return {'answer': result, 'title': '', 'address': ''}    

    else:
        print('\n\n\n\n호출됐음\n\n\n\n')
        result, rec = keyword_based(chat_state, llm, hugging_vectorstore, hugging_retriever_baseline, location, keyword, menuplace, query_rewrite, original_question, flag_eng)
       
        # 마르코프 추가
        next_rec = None
        id_t = df[df["MCT_NM"]==rec.iloc[0]["name"]].id.values[0] # id 값
        if id_t in transition_matrix_df.index:      # id가 ts매트릭스로 오면 
            next_rec = context_based_recommendation(id_t, transition_matrix_df, visit_poi_df)   
        if result == '': 
            return {'answer': '', 'title': '', 'address': '', 'next_rec': ''}

        return {
            'answer': result, 
            'title': rec['name'][:min(3, len(rec['name']))].tolist(), 
            'address': rec['full_location'][:min(3, len(rec['full_location']))].tolist(),
            'next_rec': next_rec
        }