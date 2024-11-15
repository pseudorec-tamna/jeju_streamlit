import re
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np 
from typing import List, Tuple

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

def remove_emoji(text):
    """
    이모지 및 기타 특수기호 내용 삭제 함수입니다.
    유저 리뷰나 키워드 등에서 자주 사용되어 DB 등록시 에러발생을 피하기 위해 사용합니다.
    """
    # 정규표현식 패턴: 한글, 알파벳, 공백, 숫자 제외 모든 문자 제거
    cleaned_text = re.sub(r'[^가-힣a-zA-Z0-9\s]', '', text)
    cleaned_text = re.sub(r'[\u2000-\u200f]', '', cleaned_text)
    cleaned_text = re.sub(r'[\u00A0\u2000-\u200f]', ' ', cleaned_text)
    cleaned_text = re.sub(r'[\u2028\u2029]', ' ', cleaned_text)
    return cleaned_text

def remain_numbers(text):
    """
    숫자만 남기는 함수입니다.
    """
    return re.sub(r'[^0-9]', '', text)

def remain_prices(text):
    """
    금액 정보만 남기는 함수입니다.
    """
    return re.sub(r'[^0-9~]', '', text)

def colon_delimiter(text):
    """
    '::'를 기준으로 key value 쌍을 만들어줍니다.
    e.g. 나무::33 , 여물::12
    """
    return re.sub(r'([가-힣a-zA-Z]+)(\d+)', r'\1::\2', text)
