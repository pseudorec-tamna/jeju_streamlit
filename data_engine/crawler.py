import time
from bs4 import BeautifulSoup 
from util import remain_numbers, colon_delimiter, remove_emoji, remain_prices
from selenium.webdriver.common.by import By
def home_tab(driver, id):
    """
    홈 탭의 정보를 수집합니다.
    홈 탭이 없는 경우, 바로 다음 탭으로 넘어갑니다.
    """
 
    ############ 홈 탭
    driver.get(f"https://m.place.naver.com/restaurant/{id}/home?entry=plt&reviewSort=recent")
    time.sleep(1) # 중요
    html = driver.page_source
    bs = BeautifulSoup(html, 'html.parser')

    open_time = bs.select_one('div.pSavy > div > a > div > div > div > span > span')
    url = bs.select_one('div.yIPfO > div > div > a')
    special_info = bs.select_one('div.TMK4W > div')
    benefit_info = bs.select_one('div.Uv6Eo > div > div')
    v_review_cnt = bs.select_one('div.dAsGb > span:nth-child(2)')
    b_review_cnt = bs.select_one('div.dAsGb > span:nth-child(3)')

    open_time = open_time.text if open_time else ''
    url = url.text if url else ''
    special_info = special_info.text.split('\xa0') if special_info else ''
    benefit_info = benefit_info.text if benefit_info else ''
    v_review_cnt = remain_numbers(v_review_cnt.text) if v_review_cnt else ''
    b_review_cnt = remain_numbers(b_review_cnt.text) if b_review_cnt else ''
    print('홈탭결과: ',open_time, url, special_info, benefit_info, v_review_cnt, b_review_cnt )
    return open_time, url, special_info, benefit_info, v_review_cnt, b_review_cnt
    
def menu_tab(driver, id):
    """
    메뉴 탭의 정보를 수집합니다.
    메뉴 탭이 없는 경우, 바로 다음 탭으로 넘어갑니다.
    """
  
    driver.get(f"https://m.place.naver.com/restaurant/{id}/menu/list")
    time.sleep(1)
    html = driver.page_source
    bs = BeautifulSoup(html, 'html.parser')

    prices = bs.select('div.GXS1X')
    menus = bs.select("span.lPzHi")

    if prices:
        prices = [remain_prices(price.text) if price else '' for price in prices]
        prices = [price.split('~')[0] if '~' in price else price for price in prices]
        prices = [int(x) for x in prices if x != '']
        if len(prices) > 0:
            max_price = max(prices)
            min_price = min(prices)
            mean_price = int(sum(prices) / len(prices))
        else:
            max_price = ''
            min_price = ''
            mean_price = ''
    else:
        prices, max_price, min_price, mean_price = '','','',''
    if menus:
        menus = [menu.text if menu else '' for menu in menus]
    else:
        menus = ''
    print('메뉴탭: ',prices, max_price, min_price, mean_price, menus )
    return prices, max_price, min_price, mean_price, menus

def info_tab(driver, id):
    """
    정보 탭의 정보를 수집합니다.
    정보 탭이 없는 경우, 바로 다음 탭으로 넘어갑니다.
    """

    driver.get(f"https://m.place.naver.com/restaurant/{id}/information")
    time.sleep(1)
    html = driver.page_source
    bs = BeautifulSoup(html, 'html.parser')
    
    amenity = bs.select('li.c7TR6')
    park_info = bs.select_one('div.TZ6eS')
    payment = bs.select('li.Np0MR')

    if amenity:
        amenity = [amen.text if amen else '' for amen in amenity]
    else:
        amenity = ''
    if payment:
        payment = [payment.text if payment else '' for payment in payment]
    park_info = park_info.text if park_info else ''
    print('정보탭:', amenity, park_info, payment)
    return amenity, park_info, payment

def review_tab(driver, id):
    """
    리뷰 탭의 정보를 수집합니다.
    리뷰 작업을 마친 뒤엔, 해당 드라이버를 이어받아 아래쪽의 리뷰 수집이 수행됩니다. 
    """
    driver.get(f"https://m.place.naver.com/place/{id}/review/visitor?entry=plt&reviewSort=recent")
    time.sleep(1) # 중요
    html = driver.page_source
    bs = BeautifulSoup(html, 'html.parser')
    # 이미지 url > 4개까지 찾아보고 추가하기
    i_url = None
    for cnt in range(1,4):
        if bs.select_one(f'#ibu_{cnt}'):
            i_url = bs.select_one(f'#ibu_{cnt}').get('src')
            break      
    if i_url is None:
        imglink = bs.select_one(f'div.fNygA > a > img')
        try:
            imglink = imglink.get_attribute_list('src') if imglink else ""
            i_url = imglink[0] if imglink else ''
        except Exception as e:
            i_url = e

    # 전체 평점
    average_score = bs.select_one('div.vWSFS > span.fNnpD').text if bs.select_one('div.vWSFS > span.fNnpD') else ''
    # top5 좋은점
    reactions = [''] * 5 
    for idx, reaction_keyword in enumerate(bs.select('li.MHaAm')):
        variable = reaction_keyword.text.split("\"")
        if len(variable) >1:
            react = variable[1]
            population = remain_numbers(variable[-1])
            reactions[idx] = react + "::" + str(population)


    # 특징 태그
    feature_tags = bs.select("div.JWiV0.khWUF.eZMAS > div > div > div > div > span")
    # 메뉴 태그
    menu_tags = bs.select('span.Me4yK')
    if feature_tags:
        feature_tags = [colon_delimiter(feature.text) if feature else '' for feature in feature_tags]
    else:
        feature_tags = ''
    if menu_tags:
        menu_tags = [colon_delimiter(menu.text) if menu else '' for menu in menu_tags]
    else:
        menu_tags = ''
    menu_tags = [item for item in menu_tags if item not in feature_tags]
    print('리뷰:', i_url, average_score, reactions, menu_tags, feature_tags)
    return i_url, average_score, reactions, menu_tags, feature_tags


def review_content(driver, id, args):
        driver.get(f"https://m.place.naver.com/place/{id}/review/visitor?entry=plt&reviewSort=recent")
        html = driver.page_source
        bs = BeautifulSoup(html, 'html.parser')
        score = bs.select_one('span.xobxM.fNnpD')
        score = score.text if score else ''

        score_cnt = bs.select_one('div.vWSFS > span:nth-child(2)')
        score_cnt = score_cnt.text.split('개')[0] if score_cnt else ""

        if args.click > 0:
                p = 0
                errored = 0
                while p <= args.click and errored <=10:
                    try:
                        driver.find_element(By.XPATH, '//*[@id="app-root"]/div/div/div/div[6]/div[2]/div[3]/div[2]/div/a').click()

                        p += 1
                        errored = 0
                    except Exception as e:
                        errored += 1
                        print('더보기 클릭 오류')
                    time.sleep(2)
                print('finish')

        html = driver.page_source
        bs = BeautifulSoup(html, 'html.parser')
        reviews = bs.select('li.pui__X35jYm.EjjAW')
        nicknames, contents, dates, revisits, reserves, waitings, keywords = [],[],[],[],[],[],[]
        for r in reviews:
            
            # nickname
            nickname = r.select_one('div.pui__JiVbY3 > span.pui__uslU0d')
            # content
            content = r.select_one('div.pui__vn15t2 > a.pui__xtsQN-')

            # date
            date_elements = r.select('div.pui__QKE5Pr > span.pui__gfuUIT > time')
            date = date_elements[0] if date_elements else None

            # revisit
            revisit_span = r.select('div.pui__QKE5Pr > span.pui__gfuUIT')
            revisit = revisit_span[1] if len(revisit_span) > 1 else None

            # waiting
            additional = r.select('div.pui__-0Ter1 > a.pui__uqSlGl > span.pui__V8F9nN')
            reserve, waiting, keyword = '', '', ''
            for rr in additional:
                if rr:
                    if "예약" in rr.text:
                        reserve = rr.text
                    elif "대기" in rr.text:
                        waiting = rr.text
                    else:
                        keyword = rr.text
            keywords.append(remove_emoji(keyword))
            reserves.append(remove_emoji(reserve))
            waitings.append(remove_emoji(waiting))
            # exception handling
            nickname = nickname.text if nickname else ''
            content = content.text if content else ''
            date = date.text if date and date else ''
            revisit = revisit.text if revisit and revisit != "N/A" else ''
            # reaction = reaction.text if reaction else ''
            # score = score.text[:2] if score else ''

            nicknames.append(remove_emoji(nickname))
            contents.append(remove_emoji(content))
            dates.append(date)
            revisits.append(remove_emoji(revisit))
        # print('리뷰콘텐츠:', nicknames, contents, dates, revisits,  reserves, waitings, keywords, score, score_cnt)
        return nicknames, contents, dates, revisits,  reserves, waitings, keywords, score, score_cnt
