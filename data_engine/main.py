
from client import MysqlClient
import pandas as pd
from selenium import webdriver
from util import att_decision
from crawler import home_tab, menu_tab, info_tab, review_tab, review_content
import time
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from sentence_transformers import SentenceTransformer
import argparse
import multiprocessing
from multiprocessing import Pool
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

def run(row, args, options = None, model = None, driver=None, mysql = None):
    try:
        # row 형성
        i = row['idx'].values[0]
        
        id = row['id'].values[0]

        # id값이 부여된 부분은 제끼기
        if id:
            if args.review == False:
                print(f"{row['MCT_NM'].values[0]} -> id 존재하므로 넘어갑니다.")
                return 
            


            ###################### 리뷰 수집 파트
            elif args.review == True and id != 'no' and len(row['MCT_NM'].values[0]) > 1:
                title = row['MCT_NM'].values[0]
                if args.process >1:
                    mysql = MysqlClient()
                    driver = webdriver.Chrome(options=options)
                    # model = SentenceTransformer('BAAI/bge-m3')
                    time.sleep(1) # 중요
                    print('구간1')
                    nicknames, contents, dates, revisits, reserves, waitings, keywords, score, score_cnt =review_content(driver, id, args)
                    print('구간2')
                    new_data = pd.DataFrame({'id':id,
                                            'MCT_NM': row['MCT_NM'].values[0],
                                            'title': row['title'].values[0],
                                            'address': row['ADDR'].values[0],
                                            'nickname': nicknames, 
                                            'date': dates,
                                            'content': contents,
                                            'revisit': revisits,
                                            'reserve': reserves,
                                            'waiting': waitings,
                                            'keyword': keywords,
                                            'score_cnt': score_cnt,
                                            'score': score})
                    
                    print('구간3')
                    # review에 추가
                    new_data.to_sql(name='reviewsdb3', con=mysql.engine, if_exists='append', index=False)
                    print(f"{row['MCT_NM'].values[0]} 리뷰 업데이트 진행 완료, 다음으로 넘어갑니다.")
                    return
                else:
                    print('구간4')
                    time.sleep(1) # 중요
                    nicknames, contents, dates, revisits, reserves, waitings, keywords,  score, score_cnt =review_content(driver, id, args)
                    new_data = pd.DataFrame({'id':id,
                                            'MCT_NM': row['MCT_NM'].values[0],
                                            'title': row['title'].values[0],
                                            'address': row['ADDR'].values[0],
                                            'nickname': nicknames, 
                                            'date': dates,
                                            'content': contents,
                                            'revisit': revisits,
                                            'reserve': reserves,
                                            'waiting': waitings,
                                            'keyword': keywords,
                                            'score_cnt': score_cnt,
                                            'score': score})
                    print('구간5')
                    # review에 추가
                    new_data.to_sql(name='reviewsdb3', con=mysql.engine, if_exists='append', index=False)
                    print(f"{row['idx'].values[0],row['MCT_NM'].values[0]} 리뷰 업데이트 진행 완료, 다음으로 넘어갑니다.")
                    return 
            else:
                return
            ########################
        if args.review == True:
            return
            

        if args.process> 1:
            mysql = MysqlClient()
            driver = webdriver.Chrome(options=options)
            model = SentenceTransformer('BAAI/bge-m3')

        address = row['ADDR'].values[0]

        print(f"\n----------------{i}번 가게 {row['MCT_NM'].values[0]}진행 시작 -------------\n")

        naver_map_search_url = f'https://m.map.naver.com/search2/search.naver?query={address}&sm=hty&style=v5'
        driver.get(naver_map_search_url)
        time.sleep(args.time) # 중요
        e = driver.find_elements(By.CSS_SELECTOR, '#ct > div.search_listview._content._ctAddress > ul > li')
        
        # 검색에서 나오지 않은 경우, id 'no'부여 후 다음으로 이동
        if len(e) == 0:
            row.loc[row['idx'] == i, 'id'] = 'no'

            # DB 업데이트
            print(F"{title}주소 쳐도 아무것도 안나오므로 넘어갑니다.")
            mysql.update_execute(row)

            return


        # 유사도 0.5 이하인 경우, 가장 유사도 높은 id만 책정 후 다음으로 이동
        similarity=''
        att_idx, similarity = att_decision(e, row['MCT_NM'].values[0], model)
        if similarity < 0.6:
            print(f" {row['MCT_NM'].values[0]} -> 비슷한 이름이 없으므로 넘어갑니다.\n가장 유사한 장소:{e[att_idx].get_dom_attribute('data-title')} \n유사도:{similarity}\n\n")
            row.loc[row['idx'] == i, 'id'] = e[att_idx].get_dom_attribute('data-id')
            row.loc[row['idx'] == i, 'title'] = e[att_idx].get_dom_attribute('data-title')

            # DB 업데이트
            mysql.update_execute(row)

            return
        
        id = e[att_idx].get_dom_attribute('data-id')
        long = e[att_idx].get_dom_attribute('data-longitude')
        lat = e[att_idx].get_dom_attribute('data-latitude')
        subway = e[att_idx].get_dom_attribute('data-issubway')
        entx = e[att_idx].get_dom_attribute('data-entx')
        enty = e[att_idx].get_dom_attribute('data-enty')
        booking = e[att_idx].get_dom_attribute('data-booking-url')
        coupon = e[att_idx].get_dom_attribute('data-coupon-url')
        tel = e[att_idx].get_dom_attribute('data-tel')
        title = e[att_idx].get_dom_attribute('data-title')
        row.loc[row['idx'] == i, 'id'] = id
        row.loc[row['idx'] == i, 'long'] =  long
        row.loc[row['idx'] == i, 'lat'] = lat
        row.loc[row['idx'] == i, 'subway'] = subway
        row.loc[row['idx'] == i, 'entx'] = entx
        row.loc[row['idx'] == i, 'enty'] = enty
        row.loc[row['idx'] == i, 'booking'] = booking
        row.loc[row['idx'] == i, 'coupon'] = coupon
        row.loc[row['idx'] == i, 'tel'] = tel
        row.loc[row['idx'] == i, 'title'] = title
        row.loc[row['idx'] == i, 'similarity'] = str(similarity)

        ############ 홈 탭
        open_time, url, special_info, benefit_info, v_review_cnt, b_review_cnt = home_tab(driver, id)

        row.loc[row['idx'] == i,  'open_time'] = open_time
        row.loc[row['idx'] == i,  'url'] = url
        row.loc[row['idx'] == i,  'special_info'] = special_info
        row.loc[row['idx'] == i,  'benefit_info'] = benefit_info
        row.loc[row['idx'] == i,  'v_review_cnt'] = v_review_cnt
        row.loc[row['idx'] == i,  'b_review_cnt'] = b_review_cnt

        ############ 메뉴 탭
        prices, max_price, min_price, mean_price, menus = menu_tab(driver, id)
        
        row.loc[row['idx'] == i,  'prices'] = str(prices)
        row.loc[row['idx'] == i,  'max_price'] = max_price
        row.loc[row['idx'] == i,  'min_price'] = min_price
        row.loc[row['idx'] == i,  'mean_price'] = mean_price
        row.loc[row['idx'] == i,  'menus'] = str(menus)

        ############ 정보 탭
        amenity, park_info, payment = info_tab(driver, id)

        row.loc[row['idx'] == i,  'amenity'] = str(amenity)
        row.loc[row['idx'] == i,  'park_info'] = str(park_info)
        row.loc[row['idx'] == i,  'payment'] = str(payment)

        ############ 리뷰 탭
        img_url, average_score, reactions, menu_tags, feature_tags = review_tab(driver, id)
        row.loc[row['idx'] == i, 'img_url'] = img_url
        row.loc[row['idx'] == i, 'average_score'] = average_score

        row.loc[row['idx'] == i,  'react1'] = reactions[0]
        row.loc[row['idx'] == i,  'react2'] = reactions[1]
        row.loc[row['idx'] == i,  'react3'] = reactions[2]
        row.loc[row['idx'] == i,  'react4'] = reactions[3]
        row.loc[row['idx'] == i,  'react5'] = reactions[4]

        row.loc[row['idx'] == i, 'menu_tags'] = str(menu_tags)
        row.loc[row['idx'] == i, 'feature_tags'] = str(feature_tags)

        # additional info에 추가
        mysql.update_execute(row) 

        # nicknames, contents, dates, revisits, reserves, waitings, keywords = review_content(driver, id, args)

        # new_data = pd.DataFrame({'title': title,
        #                         'address': address,
        #                         'id':id,
        #                         'nickname': nicknames, 
        #                         'content': contents,
        #                         'date': dates,
        #                         'revisit': revisits,
        #                         'reserve': reserves,
        #                         'waiting': waitings,
        #                         'keyword': keywords})
        # # review에 추가
        # new_data.to_sql(name='reviewsdb', con=mysql.engine, if_exists='append', index=False)
        # print(f"{title} 리뷰 업데이트 진행 완료, 다음으로 넘어갑니다.")
        if args.clear: 
            os.system('clear')
        return
    
    except Exception as e:
        print(f"{row['MCT_NM'].values[0]}진행 시 오류 발생\n오류 원인:{e}\n----------------------------------------\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--process", default=1, type=int)
    parser.add_argument("--start", default=0, type=int)
    parser.add_argument("--end", default=9000, type=int)
    parser.add_argument("--headless", default=False, type=bool)
    parser.add_argument("--clear", default=False, type=bool)
    parser.add_argument("--time", default=2, type=int)
    parser.add_argument("--review", default = False, type = bool)
    parser.add_argument("--click", default = 0, type = int)
    args= parser.parse_args()

    caps = DesiredCapabilities.CHROME
    caps["pageLoadStrategy"] = "none"

    options = webdriver.ChromeOptions()
    if args.headless:
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
    
    # 임베딩 모델 임포트
    model = SentenceTransformer('BAAI/bge-m3')

    # mysql 객체 선언
    mysql = MysqlClient()
    start = args.start
    end = args.end

    query = f"select * from tamdb.detailed_info_new_test3 where idx BETWEEN {start} and {end}"
    mysql.cursor.execute(query)
    rows = mysql.cursor.fetchall()

    columns = [i[0] for i in mysql.cursor.description]  # 컬럼 이름 가져오기
    df = pd.DataFrame(rows, columns=columns)
    df= df.fillna('')
    
    if args.process > 1:
    
        pool_args  = []
        print('멀티프로세스')
        for i in df['idx'].values:
            pool_args.append((df[df['idx'] == i], args, options))
        with multiprocessing.Pool(args.process) as pool:
            pool.starmap(run, pool_args)

    else:
        driver = webdriver.Chrome(options=options)
        # 단일 프로세스 처리
        print('단일프로세스')
        for i in df['idx'].values:
            row = df[df['idx'] == i]
            run(row, args, options, model, driver, mysql)











