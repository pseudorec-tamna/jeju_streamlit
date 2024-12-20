
import pandas as pd
import os
import random
import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from utils.chat_state import ChatState
from utils.prompts import chat_prompt_template, multi_turn_prompt_template, recommendation_keyword_prompt_template
from recommendation.utils import json_format
from langchain_core.runnables import RunnablePassthrough
from recommendation.utils import sub_task_detection
from recommendation.distance_based import  coordinates_based_recommendation
import requests, time
from recommendation.context_based import context_based_recommendation
from utils.lang_utils import pairwise_chat_history_to_msg_list
from utils.client import get_vectordb, df, df_refer, send_location_to_flask, FLASK_SERVER_URL
vdb = get_vectordb()


path_visit_additional_info = './data/poi_df.csv' # 방문이력 데이터에 대한 id 크롤링 따로 진행
path_transition_matrix = './data/transition_matrix.csv'

transition_matrix_df = pd.read_csv(path_transition_matrix)
visit_poi_df = pd.read_csv(path_visit_additional_info)

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_memory(input, chat_state):
    print("--memory START")
    memory_vars = chat_state.memory.load_memory_variables({})
    memory_vars["chat_history"] = pairwise_chat_history_to_msg_list(chat_state.chat_history)
    print("--memory END")
    return memory_vars.get("chat_history", [])

def keyword_based(chat_state, hugging_vectorstore, hugging_retriever_baseline, location, keyword, menuplace, query_rewrite):
    print("--Keyword Based START")
    # 정확한 주소 검색 후 못찾으면 contains로 검색 
    retrieved = df[df['ADDR_detail'] == location]
    if len(retrieved) == 0:
        retrieved = df[df['ADDR_detail'].str.contains(location)]
    
    if len(retrieved) == 0:
        retrieved = df[df['MCT_NM'] == location]

    if len(retrieved) == 0:
        retrieved = df[df['MCT_NM'].str.contains(location)]

    if len(retrieved) == 0:
        retrieved = df_refer[df_refer['MCT_NM'].str.contains(location)]
    
    filtered_location = retrieved['ADDR_detail'].unique()
    print(f'------------filtered_location: {filtered_location, type(filtered_location)}')
    menu_keywords = [c for c in chat_state.info_menuplace if c != '']
    print(f'------------menu keywords: {menu_keywords}')
    # 메뉴 키워드가 하나일 경우 직접 조건을 적용, 여러 개일 경우 $or 조건을 적용
    df['contains_keyword'] = df.apply(lambda row: any(keyword in row['menus'] or keyword in row['MCT_NM'] for keyword in menu_keywords), axis=1)
    
    
    mct_nm_list = list(df[df["contains_keyword"]]["MCT_NM"].unique())
    del df['contains_keyword']  # 삭제 후에 다른 코드와 연결

    print(f'------------mct_nm_list: {mct_nm_list}')

    # "name" 필드에 대한 필터 조건을 미리 준비
    name_condition = {"name": {"$in": mct_nm_list}} if len(mct_nm_list) > 0 else {}
    print(f'------------name condition: {name_condition}')
    if len(name_condition)!=0:
        # hugging_retriever 설정
        hugging_retriever = hugging_vectorstore.as_retriever(
            search_type='similarity_score_threshold',
            search_kwargs={
                'score_threshold': 0.001,
                'k': 100,
                'filter': {
                    "$and": [
                        {"location": {"$in": list(filtered_location)}},
                        *([name_condition] if name_condition else [])  # name_condition이 있으면 추가
                    ]
                }
            }
        )

    else:
        # hugging_retriever 설정
        hugging_retriever = hugging_vectorstore.as_retriever(
            search_type='similarity',
            search_kwargs={
                'k': 100,
                'filter': {
                    "location": {"$in": list(filtered_location)},
                }
            }
        )

    row = []
    # 키워드를 넣어 문서 검색
    if len(keyword) != 0 :
        print('키워드 있음', keyword)
        docs = hugging_retriever.invoke(
            ' '.join(keyword)
        )
    else:
        print('키워드 앖음')
        print("Keyword - Query Rewrite:", query_rewrite)
        docs = hugging_retriever.invoke(
            ' '.join(query_rewrite)
        )
    for doc in docs:
        row.append(doc.metadata)
    rec = pd.DataFrame(row).reset_index()

    """
    답변 {'recommendation_factors': {'location': '서귀포시', 'menu_place': ['고기국수'], 'keyword': ['현지인들이 많이 가는'], 'business_type': ['단품요리 전문', '가정식', '분식']}, 'processing': "The user provided '서귀포시' as a location, which means they want to find a '고기국수' restaurant in '서귀포시'. Since the user has narrowed down their search by providing a location, and we have the 'keyword' and 'menu_place' from the previous conversation, this time we will choose 'Keyword-based' recommendation.", 'original_question': '제주도 고기국수 맛집 중에서 현지인들이 많이 가는 곳 추천해줘. 서귀포시', 'response_type': 'Keyword-based'}
    # 변수 정보 : ['index', 'average_price', 'average_score', 'companion_info', 'feature_info', 'full_location', 'location', 'menu_info', 'name', 'payment_method', 'reservation_info', 'review_counts', 'review_summary', 'revisit_info', 'type', 'waiting_info']
    # average_score or review_counts를 기준으로 정렬하기 
    """

    print(f"\n\n\n\n결과값 조회: {rec}\n\n\n\n")

    if rec.shape[0] != 0:
        print(rec.columns)
        has_missing_review_counts = (rec["review_counts"] == '') | (rec["review_counts"].isna())
        has_missing_average_score = (rec["average_score"] == '') | (rec["average_score"].isna())

        # 조건에 따라 정렬 수행
        if has_missing_review_counts.any() and has_missing_average_score.any():
            # 두 열 모두 기준으로 내림차순 정렬
            rec = rec.sort_values(by=["review_counts", "average_score"], ascending=[False, False]).reset_index(drop=True)
        elif has_missing_review_counts.any():
            # 'review_counts' 기준으로만 내림차순 정렬
            rec = rec.sort_values(by=["review_counts"], ascending=[False]).reset_index(drop=True)

    # Reranking 돌리면 될 듯 
    ## 네이버 평점 통해서 돌리기 + 최소 threshold 

    # 검색이 안된 경우 - 1
    if len(rec) == 0:
        print("fallback 돌아감? - 1")
        # fall back
        if (len(menuplace) == 1) & (menuplace[0]==""):
            menuplace = random.sample(["고기국수", "갈치조림", "전복죽", "성게덮밥", "우니덮밥", "흑돼지", "설렁탕", "문어해물전골", "제주해물라면", "메밀막국수", "성게보말국", "고등어회", "두루치기", "명태조림", "딱새우", "라면", "보말"], 5)
        docs = hugging_retriever_baseline.invoke(location + ' '.join(keyword) + ' '.join(menuplace))
        for doc in docs:
            row.append(doc.metadata)
        rec = pd.DataFrame(row).reset_index()

    print("--Keyword Based END")

    return rec

def keyword_based_llm(chat_state, original_question, rec, llm, flag_eng):
    chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state))|  recommendation_keyword_prompt_template | llm | StrOutputParser()
    result = chain.invoke({"question": original_question, "recommendations": rec.loc[:2, ['name', 'full_location', 'review_summary']].to_markdown(), "flag_eng":flag_eng})
    
    # 추천 후 초기화
    chat_state.info_menuplace = ['']
    chat_state.info_location = ''
    chat_state.info_keyword = ['']
    chat_state.info_business_type = ['']
    chat_state.original_question = ''
    return result

def get_hw_response(chat_state: ChatState):
    # 한국어 Or 영어
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
    query_rewrite = chat_state.query_rewrite = recommendation_factors["query_rewrite"] 
    
    if response_type == "Chat": 
        chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | chat_prompt_template | llm | StrOutputParser()
        result = chain.invoke({"question": chat_state.message, "flag_eng":flag_eng})
        rec = None # 변수 초기화
        return {'answer': result, 'title': '', 'address': '', 'next_rec':''}    

    elif response_type == "Distance-based":
        # coord = get_coordinates_by_question(chat_state.message)
        # if "coordinates_received" not in st.session_state:
        #     st.session_state.coordinates_received = False
        if 'screen_active' not in st.session_state:
            st.session_state['screen_active'] = False

#        with open(base_dir+"/data/location.txt", "w", encoding="utf-8") as file:
#            file.write(location)
        send_location_to_flask(location)
        st.write("어느 위치에서 출발하시나요? 정확한 주소를 지도에서 검색 후 클릭해주세요. (한 번만 클릭하고 잠시 기다려주세요!)")
        screen = st.components.v1.iframe(f'{FLASK_SERVER_URL}', width=650, height=600)
        if not st.session_state['screen_active']:
            st.session_state['screen_active'] = True
        while st.session_state['screen_active']: 
            response = requests.get(f'{FLASK_SERVER_URL}/get_coordinates')
            coordinates = response.json()
            latitude = coordinates['latitude']
            longitude = coordinates['longitude']
            
            print(latitude)
            print(longitude)
            if latitude is not None and longitude is not None:
                st.session_state['screen_active'] = False
                break
            time.sleep(1)
        
        rec = coordinates_based_recommendation((longitude, latitude), df)
        mct_nm_list = rec["MCT_NM"].tolist()

        row = []
        hugging_retriever_distance = hugging_vectorstore.as_retriever(
            search_kwargs={
                'filter': {
                    "name": {"$in": mct_nm_list}  # "name" 필드가 mct_nm_list에 포함되는지 확인
                }
            }
        )
        # print("chat_state.message", chat_state.message)
        print("- Query Rewrite:", query_rewrite)
        docs = hugging_retriever_distance.invoke(query_rewrite)
        print("--Retreiver")
        for doc in docs:
            row.append(doc.metadata)
        rec = pd.DataFrame(row).reset_index()

        # 문서가 없는 경우
        if len(rec) == 0:
            # fall back
            print("- Fall Back - Query Rewrite:", query_rewrite)
            docs = hugging_retriever_baseline.invoke(query_rewrite)
            for doc in docs:
                row.append(doc.metadata)
            rec = pd.DataFrame(row).reset_index()

        print("-- chain LLM START")
        chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state))|  recommendation_keyword_prompt_template | llm | StrOutputParser()
        result = chain.invoke({"question": original_question, "recommendations": rec.loc[:2, ['name', 'full_location', 'review_summary']].to_markdown(), "flag_eng":flag_eng})
        print("-- chain LLM END")

        # 추천 후 초기화
        chat_state.info_menuplace = ['']
        chat_state.info_location = ''
        chat_state.info_keyword = ['']
        chat_state.info_business_type = ['']
        chat_state.original_question = ''
        with open(base_dir+"/data/location.txt", "w", encoding="utf-8") as file:
            file.write("")

        # 마르코프 추가
        print("--markov START")
        next_rec = None
        # if isinstance(rec, pd.DataFrame):
        id_t = df[df["MCT_NM"]==rec.iloc[0]["name"]].id.values[0] # id 값
        if id_t in transition_matrix_df.index:      # id가 ts매트릭스로 오면 
            next_rec = context_based_recommendation(id_t, transition_matrix_df, visit_poi_df)  
        print("--markov END")

        if result == '': 
            return {'answer': '', 'title': '', 'address': '', 'next_rec': ''}

        return {
            'answer': result, 
            'title': rec['name'][:min(3, len(rec['name']))].tolist(), 
            'address': rec['full_location'][:min(3, len(rec['full_location']))].tolist(),
            'next_rec': next_rec
        }

    elif response_type == "Keyword-based":
        print('\n\n\n\n호출됐음\n\n\n\n')
        rec = keyword_based(chat_state, hugging_vectorstore, hugging_retriever_baseline, location, keyword, menuplace, query_rewrite)
        result = keyword_based_llm(chat_state, original_question, rec, llm, flag_eng)
       
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
    elif response_type == "Multi-turn":
        chain = RunnablePassthrough.assign(chat_history=lambda input: load_memory(input, chat_state)) | multi_turn_prompt_template | llm | StrOutputParser()
        print(f"멀티턴 - 추천요소:::: \nlocation:{location}\nmenu_place:{menuplace}\nkeyword:{keyword}")
        result = chain.invoke({"question": chat_state.message, "menuplace": menuplace, "location": location, "keyword":keyword, "flag_eng":flag_eng})
        rec = keyword_based(chat_state, hugging_vectorstore, hugging_retriever_baseline, location, keyword, menuplace, query_rewrite)

        if result == '': 
            return {'answer': '', 'title': '', 'address': '', 'next_rec': ''}
        return {'answer': result, 
                'title': rec['name'][:min(3, len(rec['name']))].tolist(), 
                'address': rec['full_location'][:min(3, len(rec['full_location']))].tolist(),
                'next_rec': ''}
    else: 
        pass 
        

    return response
