import pymysql
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
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
