import pymysql
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings.huggingface import HuggingFaceEmbeddings
import boto3
import pandas as pd
import requests
import zipfile
vdb_instance = None

load_dotenv()

class MysqlClient:
    def __init__(self):
        self.endpoint = os.getenv("DB_HOST")
        self.port = 3306
        self.user = os.getenv("DB_USER")
        self.region = os.getenv("DB_REGION")
        self.dbname = os.getenv('DB_NAME')
        self.passwd = os.getenv('DB_PASSWORD')
        os.environ['LIBMYSQL_ENABLE_CLEARTEXT_PLUGIN'] = '1'
        self.db_url = f"mysql+mysqlconnector://{self.user}:{os.getenv('DB_PASSWORD')}@{self.endpoint}:{self.port}/{self.dbname}"
        self.engine = create_engine(self.db_url)
        self.conn = self.get_connection()
        self.cursor = self.conn.cursor()

    def get_connection(self):
        conn = pymysql.connect(host=self.endpoint, user=self.user, passwd=self.passwd, port=self.port,
                                     database=self.dbname)
        return conn

class vectordb:
    def __init__(self):
        # self.c_bucket_name = "tamnadb-faiss"
        # self.c_folder_path = "faiss_full_db"
        # self.c_local_path = "/tmp/faiss_full_db"
        self.c_bucket_name = "tamdadb2-chroma"
        self.c_folder_path = "chroma_db_restore"
        self.c_local_path = "/tmp/chroma_db_restore"
        self.s3 = boto3.client('s3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION'))
        self.download_s3_folder(self.c_bucket_name, self.c_folder_path, self.c_local_path)
        self.embedding = self.embedding_model()
        self.hugging_vectorstore = Chroma(persist_directory=self.c_local_path + '/chroma_db_restore', embedding_function=self.embedding)
    def download_s3_folder(self, bucket_name, folder_path, local_path):
        print('vectorDB 다운로드중')
        os.makedirs(local_path, exist_ok=True)
        if not os.path.exists(os.path.join(local_path, 'chroma_db_restore')):
            for obj in self.s3.list_objects_v2(Bucket=bucket_name, Prefix=folder_path)['Contents']:
                # S3 키에서 파일 이름 추출 후 로컬에 저장
                print('obj', obj)
                file_key = obj['Key']
                if file_key.endswith('/'):
                    continue  # 폴더 경로는 건너뜁니다.
                local_file_path = os.path.join(local_path, os.path.basename(file_key))
                self.s3.download_file(bucket_name, file_key, local_file_path)
                print('압축 해제중')
                zip_file = zipfile.ZipFile(local_file_path)
                zip_file.extractall(local_path)
                print('압축 해제 완료')
        else:
          print('이미 벡터스토어가 존재합니다.')

    def embedding_model(self):
        print('임베딩모델 다운로드중')
        # Embedding 모델 불러오기 - 개별 환경에 맞는 device로 설정
        model_name = "upskyy/bge-m3-Korean"
        model_kwargs = {
            # "device": "cuda"
            # "device": "mps"
            "device": "cpu"
        }
        encode_kwargs = {"normalize_embeddings": True}
        hugging_embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs=model_kwargs,
            encode_kwargs=encode_kwargs,)
        return hugging_embeddings

def get_vectordb():
    global vdb_instance
    if vdb_instance is None:
        vdb_instance = vectordb()  # 인스턴스를 한 번만 생성
    return vdb_instance
def run_query(query):
    mysql = MysqlClient()
    
    mysql.cursor.execute(query)
    print('쿼리 실행 성공')
    rows = mysql.cursor.fetchall()
    columns = [i[0] for i in mysql.cursor.description]  # 컬럼 이름 가져오기
    mysql.cursor.close()
    return pd.DataFrame(rows, columns=columns)

# Flask 서버 URL
FLASK_SERVER_URL = os.getenv('FLASK_SERVER_URL')

def send_location_to_flask(location):
    """
    Streamlit에서 입력받은 location 값을 Flask 서버에 전달.
    """
    try:
        response = requests.post(
            f"{FLASK_SERVER_URL}/set_search",
            json={"keyword": location},
        )
        if response.status_code == 200:
            print("Flask 서버로 location 전달 성공:", response.json())
        else:
            print("Flask 서버로 location 전달 실패:", response.status_code, response.text)
    except Exception as e:
        print("Flask 서버와 통신 중 오류 발생:", str(e))


# mysql 모듈 임포트
df_query = f"select * from tamdb.detailed_info_new_test4"
attraction_query = f"select * from tamdb.attraction_info"
basic_query = f"select * from tamdb.basic_info_1"

df = run_query(df_query)
df['ADDR_detail'] = df['ADDR'].map(lambda x: ' '.join(x.split(' ')[1:3]))
df_refer = run_query(attraction_query)
df_quan = run_query(basic_query)

