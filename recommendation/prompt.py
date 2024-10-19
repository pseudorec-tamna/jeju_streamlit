## User Preference Elicitation
sub_task_detection_prompt = """Determine which of the following 4 types of responses is needed for the user's question:

- User Preference Elicitation
- Recommendation
- Chat
- Explanation
- Item Detail Search

if the user's question is about recommendation, determine the type of recommendation as well.
- Distance-based
- Attribute-based

The response format should be like JSON. Only the results of the json format must be output.

For example: 
- Input : I want to find a restaurant. 
- Output : {{'response_type': 'User Preference Elicitation'}}

For example: 
- Input : I want to find a restaurant near Jeju Airport.
- Output : {{'response_type': 'Recommendation', 'recommendation_type': 'Distance-based'}}

User's question: 
- Input : {user_question}
- Output : """

address_extract_prompt = """주어진 유저의 질문에서 주소만 추출해주세요. 
For example: 제주도 제주시 우진 해장국에서 가장 가까운 맛집을 추천해주세요. 
{{'response_type': '제주도 제주시 우진 해장국'}}

For example: 제주도 제주시 천지연 폭포 근처의 맛집을 추천해주세요. 
{{'response_type': '제주도 제주시 천지연 폭포'}}

User's question: 
{user_question}"""


template_chat_prompt = '''당신은 탐라는 맛의 탐나 모델입니다. 
사용자가 당신에게 누군지 물으면 '맛집을 추천해주는 탐나라고 소개하십시오. 
긍정적이고 발랄하게 제주도민의 느낌을 살려서 질문의 답변을 도와주세요.

당신이 할 수 있는 기능은 아래와 같습니다. 
- 근처 맛집 추천 : 사용자의 현재 위치 혹은 원하는 장소에서 가장 가까운 맛집을 추천해줍니다.(주소를 최대한 자세하게 알려주세요.) 예) 제주시 애월읍 가문동길 27-8 제주달에서 가장 가까운 맛집을 추천해주세요. 
- 다음에 갈 장소 추천 : 사용자가 마지막에 들린 장소로부터 다음으로 가장 많이 방문하는 맛집, 카페, 술집, 관광지등을 추천해줍니다.
'''

template_sql_prompt = """
Based on the table schema below, Write a MySQL query that answer the user's question:
Please proceed available variable with the given table schema. 

<table schema> 
| 컬럼명 | 설명 | 데이터 타입 | 비고 | 가능한 값 |
|--------|------|-------------|------|-----------|
| YM | 기준연월 | STRING | 202301~202312 | 202301, 202302, 202303, 202304, 202305, 202306, 202307, 202308, 202309, 202310, 202311, 202312 |
| MCT_NM | 가맹점명 | STRING | | |
| OP_YMD | 개설일자 | STRING | 가맹점개설일자 | |
| MCT_TYPE | 업종 | STRING | 요식관련 30개 업종 | 가정식, 단품요리 전문, 커피, 베이커리, 일식, 치킨, 중식, 분식, 햄버거, 양식, 맥주/요리주점, 아이스크림/빙수, 피자, 샌드위치/토스트, 차, 꼬치구이, 기타세계요리, 구내식당/푸드코트, 떡/한과, 도시락, 도너츠, 주스, 동남아/인도음식, 패밀리 레스토랑, 기사식당, 야식, 스테이크, 포장마차, 부페, 민속주점 |
| ADDR | 주소 | STRING | 가맹점주소 | |
| UE_CNT_GRP | 이용건수구간 | STRING | 월별 업종별 이용건수 분위수 구간을 6개 구간으로 집계, 상위 30% 매출 가맹점 내 분위수 구간 | 1_상위 10% 이하, 2_10~25%, 3_25~50%, 4_50~75%, 5_75~90%, 6_90% 초과(하위 10% 이하) |
| UE_AMT_GRP | 이용금액구간 | STRING | 월별 업종별 이용금액 분위수 구간을 6개 구간으로 집계, 상위 30% 매출 가맹점 내 분위수 구간 | 1_상위 10% 이하, 2_10~25%, 3_25~50%, 4_50~75%, 5_75~90%, 6_90% 초과(하위 10% 이하) |
| UE_AMT_PER_TRSN_GRP | 건당평균이용금액구간 | STRING | 월별 업종별 건당평균이용금액 분위수 구간을 6개 구간으로 집계, 상위 30% 매출 가맹점 내 분위수 구간 | 1_상위 10% 이하, 2_10~25%, 3_25~50%, 4_50~75%, 5_75~90%, 6_90% 초과(하위 10% 이하) |
| MON_UE_CNT_RAT | 월요일이용건수비중 | FLOAT | | |
| TUE_UE_CNT_RAT | 화요일이용건수비중 | FLOAT | | |
| WED_UE_CNT_RAT | 수요일이용건수비중 | FLOAT | | |
| THU_UE_CNT_RAT | 목요일이용건수비중 | FLOAT | | |
| FRI_UE_CNT_RAT | 금요일이용건수비중 | FLOAT | | |
| SAT_UE_CNT_RAT | 토요일이용건수비중 | FLOAT | | |
| SUN_UE_CNT_RAT | 일요일이용건수비중 | FLOAT | | |
| HR_5_11_UE_CNT_RAT | 5시11시이용건수비중 | FLOAT | | |
| HR_12_13_UE_CNT_RAT | 12시13시이용건수비중 | FLOAT | | |
| HR_14_17_UE_CNT_RAT | 14시17시이용건수비중 | FLOAT | | |
| HR_18_22_UE_CNT_RAT | 18시22시이용건수비중 | FLOAT | | |
| HR_23_4_UE_CNT_RAT | 23시4시이용건수비중 | FLOAT | | |
| LOCAL_UE_CNT_RAT | 현지인이용건수비중 | FLOAT | 고객 자택 주소가 제주도인 경우를 현지인으로 정의 | |
| RC_M12_MAL_CUS_CNT_RAT | 최근12개월남성회원수비중 | FLOAT | 기준연월 포함 최근 12개월 집계한 값 | |
| RC_M12_FME_CUS_CNT_RAT | 최근12개월여성회원수비중 | FLOAT | 기준연월 포함 최근 12개월 집계한 값 | |
| RC_M12_AGE_UND_20_CUS_CNT_RAT | 최근12개월20대이하회원수비중 | FLOAT | 기준연월 포함 최근 12개월 집계한 값 | |
| RC_M12_AGE_30_CUS_CNT_RAT | 최근12개월30대회원수비중 | FLOAT | 기준연월 포함 최근 12개월 집계한 값 | |
| RC_M12_AGE_40_CUS_CNT_RAT | 최근12개월40대회원수비중 | FLOAT | 기준연월 포함 최근 12개월 집계한 값 | |
| RC_M12_AGE_50_CUS_CNT_RAT | 최근12개월50대회원수비중 | FLOAT | 기준연월 포함 최근 12개월 집계한 값 | |
| RC_M12_AGE_OVR_60_CUS_CNT_RAT | 최근12개월60대이상회원수비중 | FLOAT | 기준연월 포함 최근 12개월 집계한 값 | |
</table schema> 

<data sample> 
Table Name : basic_info
| YM | MCT_NM | OP_YMD | MCT_TYPE | ADDR | UE_CNT_GRP | UE_AMT_GRP | UE_AMT_PER_TRSN_GRP | MON_UE_CNT_RAT | TUE_UE_CNT_RAT | WED_UE_CNT_RAT | THU_UE_CNT_RAT | FRI_UE_CNT_RAT | SAT_UE_CNT_RAT | SUN_UE_CNT_RAT | HR_5_11_UE_CNT_RAT | HR_12_13_UE_CNT_RAT | HR_14_17_UE_CNT_RAT | HR_18_22_UE_CNT_RAT | HR_23_4_UE_CNT_RAT | LOCAL_UE_CNT_RAT | RC_M12_MAL_CUS_CNT_RAT | RC_M12_FME_CUS_CNT_RAT | RC_M12_AGE_UND_20_CUS_CNT_RAT | RC_M12_AGE_30_CUS_CNT_RAT | RC_M12_AGE_40_CUS_CNT_RAT | RC_M12_AGE_50_CUS_CNT_RAT | RC_M12_AGE_OVR_60_CUS_CNT_RAT |
|-----|--------|--------|----------|------|------------|------------|---------------------|----------------|----------------|----------------|----------------|----------------|----------------|----------------|---------------------|----------------------|----------------------|----------------------|---------------------|-------------------|--------------------------|--------------------------|----------------------------------|----------------------------|----------------------------|----------------------------|----------------------------------|
| 202301 | 통큰돼지 | 20110701 | 가정식 | 제주 제주시 용담이동 2682-9번지 통큰돼지 | 5_75~90% | 4_50~75% | 3_25~50% | 0.16129 | 0.032258 | 0.129032 | 0.096774 | 0.16129 | 0.16129 | 0.258065 | 0.0 | 0.0 | 0.16129 | 0.83871 | 0.0 | 0.707763 | 0.61 | 0.39 | 0.103 | 0.124 | 0.245 | 0.387 | 0.142 |
| 202301 | 해변 | 20050407 | 단품요리 전문 | 제주 제주시 애월읍 애월리 410-6번지 | 3_25~50% | 2_10~25% | 2_10~25% | 0.090909 | 0.121212 | 0.045455 | 0.136364 | 0.181818 | 0.242424 | 0.181818 | 0.015152 | 0.181818 | 0.242424 | 0.560606 | 0.0 | 0.230928 | 0.542 | 0.458 | 0.221 | 0.201 | 0.195 | 0.244 | 0.139 |
</data sample>

단, 기준연월에 대한 언급이 없으면 WHERE YM = '202312'을 기본으로 추가해주세요. 
SELECT는 MCT_NM만 추출하면 됩니다. 

Question: {question}
SQL Query:"""