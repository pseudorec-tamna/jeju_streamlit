from sentence_transformers import SentenceTransformer
import pandas as pd
from tqdm import tqdm
import numpy as np
import chromadb
from chromadb.config import Settings


def get_summary(merge_df):
    merge_df = merge_df.drop_duplicates('id')
    merge_df = merge_df[merge_df.id != 'no']
    merge_df = merge_df[~merge_df.id.isna()]

    merge_df['MCT_NM_NEW'] = merge_df['MCT_NM'].apply(lambda x: '' if (pd.isna(x) or x == '' or x == '[]') else f'가게 이름은 {str(x)[:50]}(이)야. ')
    merge_df['MCT_TYPE'] = merge_df['MCT_TYPE'].apply(lambda x: '' if (pd.isna(x) or x == '' or x == '[]') else f'가게 종류는 {str(x)[:50]}(이)야. ')
    merge_df['ADDR'] = merge_df['ADDR'].apply(lambda x: '' if (pd.isna(x) or x == '' or x == '[]') else f'주소는 {x}(이)야. ')
    # merge_df['average_score'] = merge_df['average_score'].apply(lambda x: '' if (pd.isna(x) or x == '' or x == '[]') else f'전반적인 평점 정보는 {str(x)}(이)야. ')
    # merge_df['react1'] = merge_df['react1'].apply(lambda x: '' if (pd.isna(x) or x == '' or x == '[]') else f'고객 리뷰 1위 사유는 {str(x)}(이)야. ')
    # merge_df['react2'] = merge_df['react2'].apply(lambda x: '' if (pd.isna(x) or x == '' or x == '[]') else f'고객 리뷰 2위 사유는 {str(x)}(이)야. ')
    # merge_df['react3'] = merge_df['react3'].apply(lambda x: '' if (pd.isna(x) or x == '' or x == '[]') else f'고객 리뷰 3위 사유는 {str(x)}(이)야. ')
    # merge_df['react4'] = merge_df['react4'].apply(lambda x: '' if (pd.isna(x) or x == '' or x == '[]') else f'고객 리뷰 4위 사유는 {str(x)}(이)야. ')
    # merge_df['react5'] = merge_df['react5'].apply(lambda x: '' if (pd.isna(x) or x == '' or x == '[]') else f'고객 리뷰 5위 사유는 {str(x)}(이)야. ')
    merge_df['amenity'] = merge_df['amenity'].apply(lambda x: '' if (pd.isna(x) or x == '' or x == '[]') else f'가게 시설 특징은 {str(x)[:50]} 등(이)야. ')
    merge_df['park_info'] = merge_df['park_info'].apply(lambda x: '' if (pd.isna(x) or x == '' or x == '[]') else f'주차 정보는 {str(x)}(이)야. ')
    merge_df['prices'] = merge_df['prices'].apply(lambda x: '' if (pd.isna(x) or x == '' or x == '[]') else f'가격 정보는 {str(x)[:50]} 등(이)야. ')
    # merge_df['mean_price'] = merge_df['mean_price'].apply(lambda x: '' if (pd.isna(x) or x == '' or x == '[]') else f'평균 메뉴의 가격 정보는 {str(x)}(이)야. ')
    merge_df['menus'] = merge_df['menus'].apply(lambda x: '' if (pd.isna(x) or x == '' or x == '[]') else f'판매하는 메뉴 정보는 {str(x)[:50]} 등 있어. ')
    # merge_df['open_time'] = merge_df['open_time'].apply(lambda x: '' if (pd.isna(x) or x == '' or x == '[]') else f'영업시간 정보는 {str(x)}(이)야. ')
    # merge_df['benefit_info'] = merge_df['benefit_info'].apply(lambda x: '' if (pd.isna(x) or x == '' or x == '[]')  else f'가게 시설 특징은 {str(x)}(이)야. ')
    # merge_df['v_review_cnt'] = merge_df['v_review_cnt'].apply(lambda x: '' if (pd.isna(x) or x == '' or x == '[]') else f'리뷰 수는 {str(x)}(이)야. ')
    # merge_df['b_review_cnt'] = merge_df['b_review_cnt'].apply(lambda x: '' if (pd.isna(x) or x == '' or x == '[]')  else f'리뷰 수는 {str(x)}(이)야. ')
    merge_df['feature_tags'] = merge_df['feature_tags'].apply(lambda x: '' if (pd.isna(x) or x == '' or x == '[]') else f'가게 특징별 리뷰 개수는 {str(x)}(이)야. ')
    merge_df['menu_tags'] = merge_df['menu_tags'].apply(lambda x: '' if (pd.isna(x) or x == '' or x == '[]') else f'가게 메뉴별 리뷰 개수는 {str(x)}(이)야. ')
    merge_df['summary'] = merge_df['MCT_NM_NEW'] + merge_df['MCT_TYPE'] + merge_df['ADDR'] + merge_df['feature_tags'] + merge_df['menu_tags'] + merge_df['park_info'] + merge_df['menus'] + merge_df['prices'] + merge_df['amenity']
    return merge_df


def encode_poi_attributes(merge_df):
    
    # load SBERT model
    model = SentenceTransformer('upskyy/bge-m3-Korean') # 1024

    restaurant_metadata = merge_df.summary.values
    batch_size = 64

    restaurant_embeddings = []

    for i in tqdm(range(0, len(restaurant_metadata), batch_size)):
        batch_texts = restaurant_metadata[i:i + batch_size]
        batch_embeddings = model.encode(batch_texts)
        restaurant_embeddings.append(batch_embeddings)

    restaurant_embeddings = np.vstack(restaurant_embeddings)

    # Use Settings for persistence configuration
    client = chromadb.PersistentClient(path="./data/chroma_persistent")

    # 기존 또는 새 컬렉션 생성 (존재하지 않으면 새로 생성)

    client.delete_collection("poi_embeddings")
    collection = client.get_or_create_collection("poi_embeddings")

    collection.add(
        documents=merge_df.summary.values.tolist()[:len(restaurant_embeddings)],
        embeddings=restaurant_embeddings.tolist()[:len(restaurant_embeddings)],
        ids=merge_df.id.values.tolist()[:len(restaurant_embeddings)]
    )

def load_collection_db():
    # 서버 재시작 후 ChromaDB 클라이언트 초기화 (영구 저장된 데이터를 불러옴)
    client2 = chromadb.PersistentClient(path="./data/chroma_persistent")
    # 기존 컬렉션 불러오기
    collection = client2.get_collection("poi_embeddings")
    return collection

def content_based_recommendation(question, collection, merge_df):

    # 컬렉션에서 데이터를 확인하거나 검색 수행
    results = collection.query(
        query_embeddings=model.encode([question]).tolist(),
        n_results=5
    )

    rec = merge_df[merge_df.id.isin(results['ids'][0])][[
                "MCT_NM", "MCT_TYPE", "ADDR", "booking", "react1", "react2", "react3", "react4", "react5"
            ]].head()
    
    return {
        "recommendation": rec,
    #     "distance_info": distance_info
    }