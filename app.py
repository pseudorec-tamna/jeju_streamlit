from flask import Flask, render_template, request, jsonify
import os

app = Flask(__name__)

# 전역 변수로 위도와 경도 저장
latitude = None
longitude = None
search_keyword = None
base_dir = os.path.dirname(os.path.abspath(__file__))


#@app.route("/")
#def index():
#    # 위치 파일에서 검색 키워드를 읽음
#    location_file = os.path.join(base_dir, "data", "location.txt")
#    if os.path.exists(location_file):
#        with open(location_file, "r", encoding="utf-8") as file:
#            location = file.read()
#    else:
#        location = "제주"  # 기본 검색 키워드
    
#    # HTML 파일을 템플릿으로 렌더링
#    return render_template("index.html", search_keyword=location)

# 메인 화면
# @app.route('/')
# def index():
#     global search_keyword
#     # location.txt에서 초기 검색어를 읽어옴
#     with open(os.path.join(base_dir, "data/location.txt"), "r", encoding="utf-8") as file:
#         search_keyword = file.read().strip() or "제주"

#     return render_template('index.html', search_keyword=search_keyword)

@app.route("/")
def index():
    """
    index.html 렌더링.
    전달된 search_keyword를 검색창 기본값으로 설정.
    """
    global search_keyword
    if not search_keyword:  # search_keyword가 없으면 기본값 설정
        search_keyword = "제주"
    return render_template("index.html", search_keyword=search_keyword)

# 검색어 저장 API
@app.route('/set_search', methods=['POST'])
def set_search():
    global search_keyword
    data = request.get_json()
    search_keyword = data.get('keyword', '제주')
    # location.txt에 저장
    with open(os.path.join(base_dir, "data/location.txt"), "w", encoding="utf-8") as file:
        file.write(search_keyword)
    return jsonify({"message": "Search keyword updated", "keyword": search_keyword})


@app.route("/click", methods=["POST"])
def handle_click():
    global latitude, longitude
    data = request.get_json()
    latitude = data["latitude"]
    longitude = data["longitude"]
    return "OK", 200


@app.route("/get_coordinates", methods=["GET"])
def get_coordinates():
    global latitude, longitude
    coords = {"latitude": latitude, "longitude": longitude}
    # 데이터 초기화
    latitude = None
    longitude = None
    return jsonify(coords)


if __name__ == "__main__":
    app.run(port=5000)

