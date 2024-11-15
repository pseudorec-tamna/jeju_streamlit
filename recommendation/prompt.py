

sub_task_detection_prompt = """
GOAL:
* You are a bot which can route user's question for giving appropriate recommendation
* Determine which of the following 4 types of responses is needed for the user's question:

RESPONSE TYPE:
- Chat
    * It applies to general conversation and all other chat.
- Multi-turn
    * It applies to queries that include a recommendation purpose, like "맛집 추천," even if there isn't much information provided but the intent is clear.
    * For multi-turn, the user's message should be included in the original_question parameter.
- Distance-based Recommendation
    * It's a distance-based model which doesn't need Multi-turn. Select this when the query includes distance-related keywords such as '근처', '가까운', '~에서 갈만한'
    * It is also possible to provide an answer after a multi-turn conversation. In particular, if terms like 'nearby' or 'close' are present, a distance-based recommendation will be selected.
- Keyword-based Recommendation
    * It's a keyword-based condition model. If there's no aggregatable and conditional information in the query, but relevant keywords are present, this model will recommend similar items based on keyword similarity.

PROCEDURE:
    * If the user's question is about Keyword-based recommendation:
        1. Analyze the question to determine if it contains any elements related to 'location', 'menu_place', or 'keyword'.
            * Gather the location, menu_place, and keyword information, then check if there are two or more elements.
            * Based on this, go through the PROCESSING to determine the type: Multi-turn or Recommendation.
                a. Identify the 'location', 'menu_place', and 'keyword' elements in the question for recommendation purposes.
                b. In the 'menu_place' part, map it to some of the following elements and add them to the 'business_type' list. Regardless of the number, map the relevant ones and add them to the list. This will later add the corresponding business type to the menu.
                    - business_type elements: ['패밀리 레스토랑', '단품요리 전문', '가정식', '햄버거', '구내식당/푸드코트', '도시락', '커피', '맥주/요리주점', '분식', '베이커리', '차', '치킨', '양식', '일식', '피자', '꼬치구이', '중식', '포장마차', '아이스크림/빙수', '떡/한과', '샌드위치/토스트', '주스', '스테이크']
                c. If a specific menu or place, such as a '식당', 가게, or '맛집', cannot be determined, it cannot be categorized under any factor 'location', 'menu_place', 'keyword'.
                d. Do not include the word '맛집' in the results.
        2. Check if the query is a response from the user to the previously generated Multi-turn conversation.
            * If the input is a short response or lacks specific details (e.g., just naming a menu item or place like '횟집', '흑돼지'), it can be a reply aimed at multi-turn conversations.
            * [Important] For Distance-based recommendations, if expressions like '근처', '가까운', or '[location]에서 갈만한' are present, perform the task without a Multi-turn process.
            * Use the 'original_question' variable to determine if it is Multi-turn. When the user's query includes 'original_question', it can be considered based on a multi-turn interaction.
        3. If there are two or more elements for recommendation based on the information and existing data, select this recommendation type from the options.
        4. Rewrite the query for clarity and accuracy, storing the result in 'query_rewrite'.
            * Identify the main intent of the query, ensuring it captures the user's primary purpose.
            * Add clarity by expanding ambiguous terms and refining grammar, phrasing, and keywords to improve relevance.
            * Remove unnecessary elements and ensure concise wording, focusing on essential information.
            * When performing the rewrite, incorporate any available information from 'location', 'menu_place', 'keyword', or 'business_type' to create a more precise, condensed query.            
    
    * If the user's question is about Distance-based recommendation:
        1. Analyze the query; if terms like 'nearby' or 'close' are present, or if it relates to distance, select Distance-based.
        2. If there is a specific menu or condition, choose Keyword-based.

    * If the user's question is about Multi-turn:
        * If the query is simple, it may be a response to the previous question.
        * Check the previous message and 'original_question'. If the response is based on a previous conversation, select Multi-turn.
        * If there are fewer than two elements within [location, menu_place, keyword] for recommendation, ask for more information.
            - Return 'Multi-turn'.
            - If information about the 'menu_place' is needed, generate a question asking the user for specifics.
            - If 'location' information is required, ask the user where the desired location is.
        * Store 'original_question' in the state for the next question and reference it later.

    * If the user's question is about Chat:
        * Respond to the user's query if it is general chat.
        * For all chats aside from recommendations and multi-turn interactions, provide a general response.
        * Handle intentionally odd phrases like '나는바보 우하하 먹포에서 가까운 애총따리 무라바키 메뉴 추천해줘'.
        * Information that appears as random typing (e.g., 'ㅁ니ㅓㅇ루 니ㅜㅣㅓㅇㄴ물ㄴㅁ일') should also be handled as Chat.

IMPORTANCE:
    * The response format should be JSON. Only output results in JSON format.
    * If a specific menu or place, such as a '식당', 가게, or '맛집', cannot be determined, it should not be categorized under 'location', 'menu_place', 'keyword'.
    * A type must always be provided, and one must be selected from four options in JSON format.
EXAMPLES:
        <example1>
        previous_gotten_info: 
        {{"location":"", "menu_place":[""], "keyword": [""], "original_question":""}}

        User's question: 
        중문 해수욕장 근처에 있는 여자친구랑 갈만한 파스타집
        
        Output:
        {{"recommendation_factors":{{"location":"중문 해수욕장", "menu_place":["파스타"], "keyword":["여자친구랑 갈 만한"], "business_type":["단품요리 전문", "가정식", "스테이크", "피자","양식"], "query_rewrite":"중문 해수욕장 근처 여자친구와 갈만한 파스타집 추천"}},
        "processing": "The location '중문 해수욕장' is provided, along with the keyword '여자친구랑 갈만한' and the menu '파스타'. '파스타' can be commonly handled in '단품요리 전문', '가정식', '스테이크', '피자', '양식'. When combined with the 'previous_gotten_info', there are three factors, and since the keyword '여자친구랑 갈 만한' is highlighted, choose the 'Keyword-based' recommendation type.",
        "original_question": "중문 해수욕장 근처에 있는 여자친구랑 갈만한 파스타집",
        "response_type": "Keyword-based"}}


        <example2>
        previous_gotten_info: 
        {{"location":"", "menu_place":[""], "keyword": [""], "original_question":""}}

        User's question: 
        중문 맛집 추천
        
        Output:
        {{"recommendation_factors":{{"location":"중문", "menu_place":[""], "keyword":[""], "business_type":[""], "query_rewrite":"중문 맛집 추천"}},
        "processing": "There is a location called '중문,' but no specific information is provided, so add the 'location' data. therefore, this time, we will choose 'Multi-turn' and register '중문 맛집 추천' in the 'original_question'.",
        "original_quesiton":"중문 맛집 추천",
        "response_type": "Multi-turn"}}


        <example3>
        previous_gotten_info: 
        {{"location":"애월", "menu_place":[""], "keyword": [""], "original_question":"애월"}}

        User's question: 
        근처 횟집
        
        Output:
        {{"recommendation_factors":{{"location":"애월", "menu_place":["횟집"], "keyword":[], "business_type": ["단품요리 전문", "가정식", "일식"], "query_rewrite":"애월 근처 횟집"}},
        "processing": "Since we have the information that the user wants '횟집' add this to the 'menu_place'. the menu's business_type can be commonly mapped as '단품요리 전문', '가정식', '일식'.With the previous 'location' '애월' already in 'previous_gotten_info', And regardless of the number of elements, if there's a comment like '근처' it should be categorized as 'Distance-based'. the original_question has to be '애월 근처 횟집'",
        "original_question": "애월 근처 횟집",
        "response_type": "Distance-based"}}

        <example4>
        previous_gotten_info: 
        {{"location":"", "menu_place":[""], "keyword": [""], "original_question":""}}

        User's question: 
        고기 맛집

        Output:
        {{"recommendation_factors":{{"location":"", "menu_place":["고기"], "keyword": [""], "business_type":["단품요리 전문","가정식","스테이크","패밀리 레스토랑","중식"], "query_rewrite":"고기 맛집"}},
        "processing": "For the input '고기 맛집' without any additional details, add it to 'menu_place'. firstly analyze the '고기', it can be mapped as '단품요리 전문', '가정식','패밀리 레스토랑','중식' as usual.Since there is no specific information from previous conversations or in 'previous_gotten_info', select a 'Multi-turn' approach to gather more information rather than making a recommendation.", 
        "original_question": "고기 맛집",
        "response_type": "Multi-turn"}}

        <example5>
        previous_gotten_info: 
        {{"location":"", "menu_place":[""], "keyword": [""], "original_question":""}}

        User's question: 
        엄마랑 갈만한곳

        Output:
        {{ "recommendation_factors":{{"location":"", "menu_place":[""],"keyword": ["엄마랑 갈만한"], "business_type":[""], "query_rewrite":}},
        "procedding": "The only specific information provided is the keyword '엄마랑 갈만한', and since '곳' was mentioned, it seems like the user wants a 'Recommendation' for anywhere. Therefore, categorize this as a 'Recommendation'. However, due to the lack of 'menu' details or 'location' information, classify it under the sub-type 'Multi-turn' to gather more information. register '엄마랑 갈만한곳' in the 'original_question'",
        "original_question": "엄마랑 갈만한곳",
        "response_type": "Multi-turn"}}

        
        <example6>
        previous_gotten_info: 
        {{"location":"", "menu_place":[""],"keyword": ["엄마랑 갈만한"], "original_question":"엄마랑 갈만한곳"}}

        User's question: 
        해물탕집

        Output:
        {{"recommendation_factors":{{"location":"", "menu_place":["해물탕"], "keyword":["엄마랑 갈만한"], "business_type":["가정식","단품요리 전문"], "query_rewrite":"엄마랑 갈만한 해물탕집 추천"}},
        "processing": "The specific menu item '해물탕' has been provided. Since the user has entered the menu they want, proceed with the 'Recommendation' type. '해물탕' can be handled in '가정식', '단품요리 전문' as usual. With the two clues of '엄마랑 갈만한' and the menu item(해물탕), proceed with the Recommendation. As both 'menuplace' and 'keyword' information are available, choose a 'Keyword-based' recommendation.",
        "original_question": "엄마랑 갈만한곳 해물탕집",
        "response_type": "Keyword-based"}}

        <example7>
        previous_gotten_info: 
        {{"location":"", "menu_place":[""], "keyword": [""], "original_question":""}}

        User's question: 
        공항 근처 먹거리

        Output:
        {{"recommendation_factors":{{"location":"공항", "menu_place":[""], "keyword": [""], "business_type":[""], "query_rewrite":"공항 근처 맛집 추천"}},
        "processing": "Based on the specific location of the airport and the expression 'nearby', it is necessary to make a recommendation using distance-based logic. Without additional information, proceed with distance-based recommendations."
        "original_question": "공항 근처 먹거리",        
        "response_type": "Distance-based"}}

        <example8>
        previous_gotten_info: 
        {{"location":"", "menu_place":[""], "keyword": [""], "original_question":""}}

        User's question: 
        오늘 날씨 좋다

        Output:
        {{"recommendation_factors":{{"location":"", "menu_place":[""], "keyword":[""], "business_type":[""], "query_rewrite":"오늘 날씨 좋다"}},
        "processing": "The conversation includes casual small talk about the weather. Select "Chat" for this scenario."
        "original_question": "",
        "response_type": "Chat"}}

        <example9>
        previous_gotten_info: 
        {{"location":"", "menu_place":[""], "keyword": [""], "original_question":""}}

        User's question: 
        ㅣㄴㅇㅁ라ㅜ닝ㅁ루니라ㅜㄴ밀

        Output:
        {{"recommendation_factors":{{"location":"", "menu_place":[""], "keyword":[""], "business_type":[""], "query_rewrite":""}},
        "processing": "It seems like the user just entered something random. Choose 'Chat' and do not collect any information."
        "original_question": "",
        "response_type": "Chat"}}        

        <example10>
        previous_gotten_info: 
        {{"location":"", "menu_place":[""], "keyword": [""], "original_question":""}}

        User's question: 
        안녕하지말고 고끼리아저씨 메뉴 추천해줘

        Output:
        {{"recommendation_factors":{{"location":"", "menu_place":[""], "keyword":[""], "business_type":[""], "query_rewrite":"고끼리아저씨 메뉴 추천"}},
        "processing": "Intentionally created confusion with the word '메뉴'; in reality, it means nothing, so it’s passed to Chat and no information is collected."
        "original_question": "",
        "response_type": "Chat"}} 
        
        <example11>
        previous_gotten_info: 
        {{"location":"", "menu_place":[""], "keyword":[""], "original_question":""}}

        User's question: 
        멍청이 똥개 근처 당근당근 추천해줘

        Output:
        {{"recommendation_factors":{{"location":"", "menu_place":[""], "keyword": [""], "business_type": [""], "query_rewrite":"멍청이 똥개 근처 당근 추천"}},
        "processing": " Although '근처' and '추천해줘' exist, I'm looking for something completely nonsensical, so it’s sent to Chat.""
        "original_question": "",
        "response_type": "Chat"}} 
        

previous_gotten_info: 
{{'location':{location}, 'menu_place':{menuplace}, 'keyword':{keyword}, 'original_question':{original_question}}} 
    
User's question: 
{user_question}

Output: 
"""

address_extract_prompt = """주어진 유저의 질문에서 주소만 추출해주세요. 
For example: 제주도 제주시 우진 해장국에서 가장 가까운 맛집을 추천해주세요. 
{{'response_type': '제주도 제주시 우진 해장국'}}

For example: 제주도 제주시 천지연 폭포 근처의 맛집을 추천해주세요. 
{{'response_type': '제주도 제주시 천지연 폭포'}}

User's question: 
{user_question}"""


template_sql_prompt = """
GOAL:
* Write a MySQL query that answers the user's question based on the following table schema and available variables.
* Ensure that you only use the variables specified in the TABLE SCHEMA section below. 

TABLE SCHEMA:
| Column Name | Description | Data Type | Notes | Possible Values |
|-------------|-------------|-----------|-------|-----------------|
| YM | Reference Month | STRING | 202301~202312 | 202301, 202302, 202303, 202304, 202305, 202306, 202307, 202308, 202309, 202310, 202311, 202312 |
| MCT_NM | Merchant Name | STRING | | |
| OP_YMD | Opening Date | STRING | Date the merchant opened | |
| MCT_TYPE | Business Type | STRING | 30 categories of dining-related types | 가정식, 단품요리 전문, 커피, 베이커리, 일식, 치킨, 중식, 분식, 햄버거, 양식, 맥주/요리주점, 아이스크림/빙수, 피자, 샌드위치/토스트, 차, 꼬치구이, 기타세계요리, 구내식당/푸드코트, 떡/한과, 도시락, 도너츠, 주스, 동남아/인도음식, 패밀리 레스토랑, 기사식당, 야식, 스테이크, 포장마차, 부페, 민속주점 |
| ADDR | Address | STRING | Merchant's address | |
| UE_CNT_GRP | Usage Count Group | STRING | Grouped into 6 levels based on usage volume by month and industry | 1_상위 10% 이하, 2_10~25%, 3_25~50%, 4_50~75%, 5_75~90%, 6_90% 초과(하위 10% 이하) |
| UE_AMT_GRP | Usage Amount Group | STRING | Grouped into 6 levels based on usage amount by month and industry | 1_상위 10% 이하, 2_10~25%, 3_25~50%, 4_50~75%, 5_75~90%, 6_90% 초과(하위 10% 이하) |
| UE_AMT_PER_TRSN_GRP | Average Transaction Amount Group | STRING | Grouped into 6 levels based on average transaction amount by month and industry | 1_상위 10% 이하, 2_10~25%, 3_25~50%, 4_50~75%, 5_75~90%, 6_90% 초과(하위 10% 이하) |
| MON_UE_CNT_RAT | Monday Usage Count Ratio | FLOAT | | |
| TUE_UE_CNT_RAT | Tuesday Usage Count Ratio | FLOAT | | |
| WED_UE_CNT_RAT | Wednesday Usage Count Ratio | FLOAT | | |
| THU_UE_CNT_RAT | Thursday Usage Count Ratio | FLOAT | | |
| FRI_UE_CNT_RAT | Friday Usage Count Ratio | FLOAT | | |
| SAT_UE_CNT_RAT | Saturday Usage Count Ratio | FLOAT | | |
| SUN_UE_CNT_RAT | Sunday Usage Count Ratio | FLOAT | | |
| HR_5_11_UE_CNT_RAT | 5 AM to 11 AM Usage Ratio | FLOAT | | |
| HR_12_13_UE_CNT_RAT | 12 PM to 1 PM Usage Ratio | FLOAT | | |
| HR_14_17_UE_CNT_RAT | 2 PM to 5 PM Usage Ratio | FLOAT | | |
| HR_18_22_UE_CNT_RAT | 6 PM to 10 PM Usage Ratio | FLOAT | | |
| HR_23_4_UE_CNT_RAT | 11 PM to 4 AM Usage Ratio | FLOAT | | |
| LOCAL_UE_CNT_RAT | Local User Usage Ratio | FLOAT | Defined as users with Jeju residence | |
| RC_M12_MAL_CUS_CNT_RAT | 12-Month Male Customer Ratio | FLOAT | Aggregated for the past 12 months | |
| RC_M12_FME_CUS_CNT_RAT | 12-Month Female Customer Ratio | FLOAT | Aggregated for the past 12 months | |
| RC_M12_AGE_UND_20_CUS_CNT_RAT | 12-Month Under-20 Customer Ratio | FLOAT | Aggregated for the past 12 months | |
| RC_M12_AGE_30_CUS_CNT_RAT | 12-Month 30s Customer Ratio | FLOAT | Aggregated for the past 12 months | |
| RC_M12_AGE_40_CUS_CNT_RAT | 12-Month 40s Customer Ratio | FLOAT | Aggregated for the past 12 months | |
| RC_M12_AGE_50_CUS_CNT_RAT | 12-Month 50s Customer Ratio | FLOAT | Aggregated for the past 12 months | |
| RC_M12_AGE_OVR_60_CUS_CNT_RAT | 12-Month Over-60 Customer Ratio | FLOAT | Aggregated for the past 12 months | |

DATA SAMPLE:
Table Name: basic_info
| YM | MCT_NM | OP_YMD | MCT_TYPE | ADDR | UE_CNT_GRP | UE_AMT_GRP | UE_AMT_PER_TRSN_GRP | MON_UE_CNT_RAT | TUE_UE_CNT_RAT | WED_UE_CNT_RAT | THU_UE_CNT_RAT | FRI_UE_CNT_RAT | SAT_UE_CNT_RAT | SUN_UE_CNT_RAT | HR_5_11_UE_CNT_RAT | HR_12_13_UE_CNT_RAT | HR_14_17_UE_CNT_RAT | HR_18_22_UE_CNT_RAT | HR_23_4_UE_CNT_RAT | LOCAL_UE_CNT_RAT | RC_M12_MAL_CUS_CNT_RAT | RC_M12_FME_CUS_CNT_RAT | RC_M12_AGE_UND_20_CUS_CNT_RAT | RC_M12_AGE_30_CUS_CNT_RAT | RC_M12_AGE_40_CUS_CNT_RAT | RC_M12_AGE_50_CUS_CNT_RAT | RC_M12_AGE_OVR_60_CUS_CNT_RAT |
|-----|--------|--------|----------|------|------------|------------|---------------------|----------------|----------------|----------------|----------------|----------------|----------------|----------------|---------------------|----------------------|----------------------|----------------------|---------------------|-------------------|--------------------------|--------------------------|----------------------------------|----------------------------|----------------------------|----------------------------|----------------------------------|
| 202301 | 통큰돼지 | 20110701 | 가정식 | 제주 제주시 용담이동 2682-9번지 통큰돼지 | 5_75~90% | 4_50~75% | 3_25~50% | 0.16129 | 0.032258 | 0.129032 | 0.096774 | 0.16129 | 0.16129 | 0.258065 | 0.0 | 0.0 | 0.16129 | 0.83871 | 0.0 | 0.707763 | 0.61 | 0.39 | 0.103 | 0.124 | 0.245 | 0.387 | 0.142 |
| 202301 | 해변 | 20050407 | 단품요리 전문 | 제주 제주시 애월읍 애월리 410-6번지 | 3_25~50% | 2_10~25% | 2_10~25% | 0.090909 | 0.121212 | 0.045455 | 0.136364 | 0.181818 | 0.242424 | 0.181818 | 0.015152 | 0.181818 | 0.242424 | 0.560606 | 0.0 | 0.230928 | 0.542 | 0.458 | 0.221 | 0.201 | 0.195 | 0.244 | 0.139 |

IMPORTANCE:
* Ensure that the address specified in the query is accurate without missing or altering any characters. For example, if the location is "이도이동," make sure to include it exactly as "%이도이동%" in the query.
* For conditions involving top or bottom percentages, ensure clarity in the MySQL query:
    - If the query requests the top 10%, select "1_상위 10% 이하" in the query.
    - If the query requests the top 20%, select "2_10~25%" in the query.
    - If the query requests the top 50%, select "3_25~50%" in the query.
    - If the query requests the top 5075%, select "4_50~75%" in the query.
    - If the query requests the top 7590%, select "5_75~90%" in the query.
    - If the query requests the top 90%, select "6_90%" in the query.
    - If the query requests the bottom 90%, select "1_상위 10% 이하" in the query.
    - If the query requests the bottom 7590%, select "2_10~25%" in the query.
    - If the query requests the bottom 50%, select "4_50~75%" in the query.
    - If the query requests the bottom 5075%, select "3_25~50%" in the query.
    - If the query requests the bottom 20%, select "5_75~90%" in the query.
    - If the query requests the bottom 10%, select "6_90%" in the query.
* If no reference month is given, use YM = '202312'.
* Only select the column MCT_NM in the query result.
* Only use the following VARIABLES:

VARIABLES: 
- YM, MCT_NM, OP_YMD, MCT_TYPE, ADDR, UE_CNT_GRP, UE_AMT_GRP, UE_AMT_PER_TRSN_GRP, MON_UE_CNT_RAT, TUE_UE_CNT_RAT, 
  WED_UE_CNT_RAT, THU_UE_CNT_RAT, FRI_UE_CNT_RAT, SAT_UE_CNT_RAT, SUN_UE_CNT_RAT, HR_5_11_UE_CNT_RAT, HR_12_13_UE_CNT_RAT, 
  HR_14_17_UE_CNT_RAT, HR_18_22_UE_CNT_RAT, HR_23_4_UE_CNT_RAT, LOCAL_UE_CNT_RAT, RC_M12_MAL_CUS_CNT_RAT, 
  RC_M12_FME_CUS_CNT_RAT, RC_M12_AGE_UND_20_CUS_CNT_RAT, RC_M12_AGE_30_CUS_CNT_RAT, RC_M12_AGE_40_CUS_CNT_RAT, 
  RC_M12_AGE_50_CUS_CNT_RAT, RC_M12_AGE_OVR_60_CUS_CNT_RAT

EXAMPLE QUESTION1: 
삼양삼동에서 야간(23시-4시) 이용 비중이 가장 낮은 단품요리 전문식당 중 남성 고객 비중이 가장 낮은 곳은?

QUESTION1 - SQL Query: 
```sql
SELECT 
    `basic_info`.`MCT_NM`
FROM 
    `basic_info`
WHERE 
    `basic_info`.`MCT_TYPE` = '단품요리 전문'
    AND `basic_info`.`ADDR` LIKE '%삼양삼동%'
    -- 야간 이용 비중이 가장 낮은 단품요리 전문식당 중에서
    AND `basic_info`.`HR_23_4_UE_CNT_RAT` = (SELECT MIN(`HR_23_4_UE_CNT_RAT`) 
                                              FROM `basic_info` 
                                              WHERE `MCT_TYPE` = '단품요리 전문' 
                                              AND `ADDR` LIKE '%삼양삼동%')
ORDER BY 
    -- 남성 고객 비중이 가장 낮은 순으로 정렬
    `basic_info`.`RC_M12_MAL_CUS_CNT_RAT` ASC
LIMIT 1;
```

EXAMPLE QUESTION2: 
성산읍에서 최근 12개월 동안 50대 고객 비중이 가장 높은 찻집은 어디인가요?

QUESTION2 - SQL Query:
```sql
SELECT 
    MCT_NM  -- 식당 이름
FROM 
    basic_info 
WHERE 
    MCT_TYPE = '차'  -- 식당 종류가 '차'인 경우
    AND ADDR LIKE '%성산읍%'  -- 주소가 '성산읍'을 포함하는 경우
    AND RC_M12_AGE_50_CUS_CNT_RAT = (  -- 50대 고객 비중이 가장 높은 경우
        SELECT 
            MAX(RC_M12_AGE_50_CUS_CNT_RAT)  -- 50대 고객 비중의 최댓값을 찾습니다.
        FROM 
            basic_info
        WHERE 
            MCT_TYPE = '차'  -- 식당 종류가 '차'인 경우
            AND ADDR LIKE '%성산읍%'  -- 주소가 '성산읍'을 포함하는 경우
    )
ORDER BY 
    RC_M12_AGE_50_CUS_CNT_RAT DESC  -- 50대 고객 비중 내림차순으로 정렬하여 가장 높은 비중을 가진 식당을 먼저 보여줍니다.
LIMIT 1;

User's Question: {question}

SQL Query:"""
