import pymysql
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
load_dotenv()

# mysql 모듈 임포트
class MysqlClient:
    def __init__(self):
        self.endpoint = os.getenv("RDS_ENDPOINT")
        self.port = 3306
        self.user = os.getenv("RDS_USER")
        self.region = os.getenv("RDS_REGION")
        self.dbname = os.getenv('RDS_NAME')
        self.passwd = os.getenv('RDS_PW')
        os.environ['LIBMYSQL_ENABLE_CLEARTEXT_PLUGIN'] = '1'
        self.db_url = f"mysql+mysqlconnector://admin:{os.getenv('RDS_PW')}@{self.endpoint}:3306/{self.dbname}"
        self.engine = create_engine(self.db_url)
        self.conn = self.get_connection()
        self.cursor = self.conn.cursor()

    def get_connection(self):
        conn = pymysql.connect(host=self.endpoint, user=self.user, passwd=self.passwd, port=self.port,
                                     database=self.dbname)
        return conn

    def update_execute(self, row):
        update_query = """
        UPDATE detailed_info_new
        SET MCT_NM = %s,
            ADDR = %s,
            title = %s,
            id = %s,
            tel = %s,
            average_score = %s,
            `long` = %s,
            lat = %s,
            entx = %s,
            enty = %s,
            subway = %s,
            booking = %s,
            coupon = %s,
            img_url = %s,
            react1 = %s,
            react2 = %s,
            react3 = %s,
            react4 = %s,
            react5 = %s,
            similarity = %s,
            amenity = %s,
            park_info = %s,
            payment = %s,
            prices = %s,
            max_price = %s,
            min_price = %s,
            mean_price = %s,
            menus = %s,
            open_time = %s,
            url = %s,
            special_info = %s,
            benefit_info = %s,
            v_review_cnt = %s,
            b_review_cnt = %s,
            menu_tags = %s,
            feature_tags = %s
        WHERE idx = %s;
        """
        # 데이터프레임의 각 행을 순차적으로 업데이트
        self.cursor.execute(update_query, (
        row['MCT_NM'].values[0], row['ADDR'].values[0], row['title'].values[0], row['id'].values[0], row['tel'].values[0], row['average_score'].values[0],
        row['long'].values[0], row['lat'].values[0], row['entx'].values[0], row['enty'].values[0], row['subway'].values[0], row['booking'].values[0], row['coupon'].values[0],
        row['img_url'].values[0], row['react1'].values[0], row['react2'].values[0], row['react3'].values[0], row['react4'].values[0], row['react5'].values[0],
        row['similarity'].values[0], row['amenity'].values[0], row['park_info'].values[0], row['payment'].values[0], row['prices'].values[0], row['max_price'].values[0],
        row['min_price'].values[0], row['mean_price'].values[0], row['menus'].values[0], row['open_time'].values[0], row['url'].values[0], row['special_info'].values[0],
        row['benefit_info'].values[0], row['v_review_cnt'].values[0], row['b_review_cnt'].values[0], row['menu_tags'].values[0], row['feature_tags'].values[0],
        row['idx'].values[0] ))

        # 데이터베이스에 변경 사항 적용
        self.conn.commit()
        print(f"{row['MCT_NM'].values[0]} -> additional table 업데이트 커밋 완료\n----------------------------------------\n")

    def update_execute_test(self, row):
        update_query = """
        UPDATE detailed_info_new_test
        SET MCT_NM = %s,
            ADDR = %s,
            title = %s,
            id = %s,
            tel = %s,
            average_score = %s,
            `long` = %s,
            lat = %s,
            entx = %s,
            enty = %s,
            subway = %s,
            booking = %s,
            coupon = %s,
            img_url = %s,
            react1 = %s,
            react2 = %s,
            react3 = %s,
            react4 = %s,
            react5 = %s,
            similarity = %s,
            amenity = %s,
            park_info = %s,
            payment = %s,
            prices = %s,
            max_price = %s,
            min_price = %s,
            mean_price = %s,
            menus = %s,
            open_time = %s,
            url = %s,
            special_info = %s,
            benefit_info = %s,
            v_review_cnt = %s,
            b_review_cnt = %s,
            menu_tags = %s,
            feature_tags = %s
        WHERE idx = %s;
        """
        # 데이터프레임의 각 행을 순차적으로 업데이트
        self.cursor.execute(update_query, (
        row['MCT_NM'].values[0], row['ADDR'].values[0], row['title'].values[0], row['id'].values[0], row['tel'].values[0], row['average_score'].values[0],
        row['long'].values[0], row['lat'].values[0], row['entx'].values[0], row['enty'].values[0], row['subway'].values[0], row['booking'].values[0], row['coupon'].values[0],
        row['img_url'].values[0], row['react1'].values[0], row['react2'].values[0], row['react3'].values[0], row['react4'].values[0], row['react5'].values[0],
        row['similarity'].values[0], row['amenity'].values[0], row['park_info'].values[0], row['payment'].values[0], row['prices'].values[0], row['max_price'].values[0],
        row['min_price'].values[0], row['mean_price'].values[0], row['menus'].values[0], row['open_time'].values[0], row['url'].values[0], row['special_info'].values[0],
        row['benefit_info'].values[0], row['v_review_cnt'].values[0], row['b_review_cnt'].values[0], row['menu_tags'].values[0], row['feature_tags'].values[0],
        row['idx'].values[0] ))

        # 데이터베이스에 변경 사항 적용
        self.conn.commit()
        print(f"{row['MCT_NM'].values[0]} -> additional table 업데이트 커밋 완료\n----------------------------------------\n")
