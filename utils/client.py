import pymysql
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings.huggingface import HuggingFaceEmbeddings
import boto3
from langchain.vectorstores import FAISS
vdb_instance = None

load_dotenv()

# mysql 모듈 임포트
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
        self.c_bucket_name = "tamnadb-chroma"
        self.c_folder_path = "chroma_db"
        self.c_local_path = "/tmp/chroma_db"
        self.s3 = boto3.client('s3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION'))
        self.download_s3_folder(self.c_bucket_name, self.c_folder_path, self.c_local_path)
        self.embedding = self.embedding_model()
        self.hugging_vectorstore = Chroma(persist_directory=self.c_local_path , embedding_function=self.embedding)
        # self.hugging_vectorstore = FAISS.load_local(
        #     folder_path=self.c_local_path,
        #     index_name="faiss_index",
        #     embeddings=self.embedding,
        #     allow_dangerous_deserialization=True,
        # )
    def download_s3_folder(self, bucket_name, folder_path, local_path):
        print('vectorDB 다운로드중')
        os.makedirs(local_path, exist_ok=True)
        for obj in self.s3.list_objects_v2(Bucket=bucket_name, Prefix=folder_path)['Contents']:
            # S3 키에서 파일 이름 추출 후 로컬에 저장
            print('obj', obj)
            file_key = obj['Key']
            if file_key.endswith('/'):
                continue  # 폴더 경로는 건너뜁니다.
            local_file_path = os.path.join(local_path, os.path.basename(file_key))
            self.s3.download_file(bucket_name, file_key, local_file_path)

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
