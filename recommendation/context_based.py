import pandas as pd
import numpy as np


from sentence_transformers import SentenceTransformer
# from selenium import webdriver

from tqdm import tqdm
import pandas as pd
import time
import os
import re
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np 
from typing import List, Tuple

def make_transition_matrix(hist_df, poi_df, shinhan_df,path_transition_matrix):

    # 신한카드 데이터 필터링 후 [신한카드POI * 이력POI] matrix 생성
    shinhan_df = shinhan_df[['id','MCT_NM']]
    shinhan_df = shinhan_df[shinhan_df.id != 'no']
    shinhan_df = shinhan_df.drop_duplicates('MCT_NM')
    shinhan_df = shinhan_df.drop_duplicates('id')

    shinhan_meta = shinhan_df[shinhan_df.id.isin(poi_df.id.unique())]

    shinhan_ids = shinhan_meta['id'].unique()

    # Create a transition matrix based on the historical data
    transition_matrix = np.zeros((len(shinhan_ids), len(shinhan_ids)))
    # Create a mapping from item names to indices
    item_to_index = {item: idx for idx, item in enumerate(shinhan_ids)}

    for user, group in hist_df[['TRAVEL_ID','id']].groupby('TRAVEL_ID'):
        previous_item = None
        for current_item in group['id']:
            if previous_item is not None:
                start_idx = item_to_index[previous_item]
                end_idx = item_to_index[current_item]
                transition_matrix[start_idx, end_idx] += 1
            previous_item = current_item

    # Normalize the transition matrix to represent probabilities
    # transition_matrix = transition_matrix / transition_matrix.sum(axis=1, keepdims=True)

    # Convert to a DataFrame for better readability
    transition_matrix_df = pd.DataFrame(transition_matrix, index=shinhan_ids, columns=shinhan_ids)
    transition_matrix_df.to_csv(path_transition_matrix)
    return transition_matrix_df


def context_based_recommendation(start_location, transition_matrix_df, visit_poi_df):
    # 다른 추천 결과의 rec['MCT_NM']을 기준으로 next visit 제안하기
    # query를 id로 받는 방식 -> 카카오맵API?
    top_3_shinhan_poi = get_top_3_end_locations(start_location, transition_matrix_df,top_k=10)
    result_id = [x[0] for x in top_3_shinhan_poi]
    rec = visit_poi_df[visit_poi_df.id.isin(result_id)]
    rec['MCT_NM'] = rec['VISIT_AREA_NM']
    rec['MCT_TYPE'] = ''
    rec['ADDR'] = rec['SEARCH_ADDR']
    rec['booking'] = ''
    rec['react1'] = ''
    rec['react2'] = ''
    rec['react3'] = ''
    rec['react4'] = ''
    rec['react5'] = ''
    rec = rec[[
            "MCT_NM", "MCT_TYPE", "ADDR", "booking", "react1", "react2", "react3", "react4", "react5"
        ]].head()
    
    return {
        "recommendation": rec,
    }


def get_top_3_end_locations(start_location, transition_matrix_df, top_k):
    if start_location not in transition_matrix_df.index:
        return "Start location not found in transition matrix."
    
    # Get the transition probabilities for the start location
    probabilities = transition_matrix_df.loc[start_location]
    
    # Get the top 3 end locations with the highest transition probabilities
    top_3_locations = probabilities.nlargest(top_k).index.tolist()
    top_3_probs = probabilities.nlargest(top_k).values.tolist()
    

    return list(zip(top_3_locations, top_3_probs))


def get_additional_info_visit_hist(path_visit_info, path_visit_additional_info):
    
    hist_df = pd.read_csv(path_visit_info)
    hist_df = hist_df[(hist_df.X_COORD > 126.117692) & (hist_df.X_COORD < 127.071811) & (hist_df.Y_COORD > 33.062919) & (hist_df.Y_COORD < 33.599581)]

    # poi 메타 생성
    poi_df = hist_df[['VISIT_AREA_NM','ROAD_NM_ADDR','LOTNO_ADDR']].drop_duplicates()

    # 주소값이 없는 poi 필터링
    poi_df['SEARCH_ADDR'] = poi_df.apply(lambda row: row['LOTNO_ADDR'] if pd.notna(row['LOTNO_ADDR']) else row['ROAD_NM_ADDR'], axis=1)
    poi_df = poi_df[~poi_df.SEARCH_ADDR.isna()]
    poi_df = poi_df.reset_index(drop=True)


    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    # 임베딩 모델 임포트
    model = SentenceTransformer('BAAI/bge-m3')

    options = webdriver.ChromeOptions()
    options.add_argument('--headless') 
    options.add_argument('--ignore-ssl-errors=yes')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_argument('--log-level=3')
    options.add_argument('--disable-gpu')
    options.add_argument('--incognito')

    # Add Image Loading inactive Flag to reduce loading time
    options.add_argument('--disable-images')
    options.add_experimental_option(
        "prefs", {'profile.managed_default_content_settings.images': 2})
    options.add_argument('--blink-settings=imagesEnabled=false')
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
    options.add_argument(f"user-agent={user_agent}")
    driver = webdriver.Chrome(options=options)

    search_id = []
    for row in tqdm(poi_df.values):
        search_id.append(search_map(row,model,driver))

    poi_df['data-id'] = [x[0] for x in search_id]
    poi_df.to_csv(path_visit_additional_info)
    return poi_df

def att_decision(att_list, title, model)-> Tuple[int, float]:
    """
    목표하는 식당의 이름과 주소지 검색 시 나온 가게들의 임베딩을 통해 가장 비슷한 이름의 가게를 선별하는 함수
    model: 임베딩 모델입니다.
    att_list: selector로 뽑아온 해당 주소지 내의 가게 이름 리스트입니다.
    title: 기존 DB에서 가져온 데이터 수집을 목표하는 가게 이름 str입니다.
    """
    embed_lst = []
    
    # 목표 가게명 인코딩
    original = model.encode(title).reshape(1,-1)
    
    # 검색된 가게명 리스트 각각 인코딩 후 유사도 검사
    for li in att_list:
        embed_lst.append(cosine_similarity(original, model.encode(li.get_dom_attribute('data-title')).reshape(1,-1))[0][0])

    # 유사도 상 가장 높은 값의 index, 그리고 유사도 값 return
    
    print(f"목표 식당: {title} / 가장 유사한 식당: {att_list[np.argmax(embed_lst)].get_dom_attribute('data-title')} 선택")
    print(f'유사도: {embed_lst[np.argmax(embed_lst)]}')
    return np.argmax(embed_lst), embed_lst[np.argmax(embed_lst)]

def search_map(row, model=None, driver=None):
    try:
        address = row[-1]
        title = row[0]
        naver_map_search_url = f'https://m.map.naver.com/search2/search.naver?query={address}&sm=hty&style=v5'
        driver.get(naver_map_search_url)
        time.sleep(2) # 중요
        e = driver.find_elements(By.CSS_SELECTOR, '#ct > div.search_listview._content._ctAddress > ul > li')
        
        # 검색에서 나오지 않은 경우, id 'no'부여 후 다음으로 이동
        if len(e) == 0:
            return ['no', title]

            # DB 업데이트
            print(F"{title}주소 쳐도 아무것도 안나오므로 넘어갑니다.")

        # 유사도 0.5 이하인 경우, id 'no'부여 후 다음으로 이동
        similarity=''
        att_idx, similarity = att_decision(e, title, model)
        print(f"검색주소:{address}")
        if similarity < 0.5:
            print(f" {title} -> 비슷한 이름이 없으므로 넘어갑니다.\n가장 유사한 장소:{e[att_idx].get_dom_attribute('data-title')} \n유사도:{similarity}\n\n")
            return ['no', title]
        else:
            id = e[att_idx].get_dom_attribute('data-id')
            title_rsp = e[att_idx].get_dom_attribute('data-title')
            return [id, title_rsp]
    except Exception as e:
        print(f"{title}진행 시 오류 발생\n오류 원인:{e}\n----------------------------------------\n")
