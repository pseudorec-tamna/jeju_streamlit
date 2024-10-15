from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# 전역 변수로 위도와 경도 저장
latitude = None
longitude = None


@app.route('/')
def index():

    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>키워드로 장소검색하고 목록으로 표출하기</title>
        <style>
            .map_wrap, .map_wrap * {margin:0;padding:0;font-family:'Malgun Gothic',dotum,'돋움',sans-serif;font-size:12px;}
            .map_wrap a, .map_wrap a:hover, .map_wrap a:active{color:#000;text-decoration: none;}
            .map_wrap {position:relative;width:100%;height:500px;}
            #menu_wrap {position:absolute;top:0;left:0;bottom:0;width:250px;margin:10px 0 30px 10px;padding:5px;overflow-y:auto;background:rgba(255, 255, 255, 0.7);z-index: 1;font-size:12px;border-radius: 10px;}
            .bg_white {background:#fff;}
            #menu_wrap hr {display: block; height: 1px;border: 0; border-top: 2px solid #5F5F5F;margin:3px 0;}
            #menu_wrap .option{text-align: center;}
            #menu_wrap .option p {margin:10px 0;}  
            #menu_wrap .option button {margin-left:5px;}
            #placesList li {list-style: none;}
            #placesList .item {position:relative;border-bottom:1px solid #888;overflow: hidden;cursor: pointer;min-height: 65px;}
            #placesList .item span {display: block;margin-top:4px;}
            #placesList .item h5, #placesList .item .info {text-overflow: ellipsis;overflow: hidden;white-space: nowrap;}
            #placesList .item .info{padding:10px 0 10px 55px;}
            #placesList .info .gray {color:#8a8a8a;}
            #placesList .info .jibun {padding-left:26px;background:url(https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/places_jibun.png) no-repeat;}
            #placesList .info .tel {color:#009900;}
            #placesList .item .markerbg {float:left;position:absolute;width:36px; height:37px;margin:10px 0 0 10px;background:url(https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/marker_number_blue.png) no-repeat;}
            #placesList .item .marker_1 {background-position: 0 -10px;}
            #placesList .item .marker_2 {background-position: 0 -56px;}
            #placesList .item .marker_3 {background-position: 0 -102px}
            #placesList .item .marker_4 {background-position: 0 -148px;}
            #placesList .item .marker_5 {background-position: 0 -194px;}
            #placesList .item .marker_6 {background-position: 0 -240px;}
            #placesList .item .marker_7 {background-position: 0 -286px;}
            #placesList .item .marker_8 {background-position: 0 -332px;}
            #placesList .item .marker_9 {background-position: 0 -378px;}
            #placesList .item .marker_10 {background-position: 0 -423px;}
            #placesList .item .marker_11 {background-position: 0 -470px;}
            #placesList .item .marker_12 {background-position: 0 -516px;}
            #placesList .item .marker_13 {background-position: 0 -562px;}
            #placesList .item .marker_14 {background-position: 0 -608px;}
            #placesList .item .marker_15 {background-position: 0 -654px;}
            #pagination {margin:10px auto;text-align: center;}
            #pagination a {display:inline-block;margin-right:10px;}
            #pagination .on {font-weight: bold; cursor: default;color:#777;}
        </style>
    </head>
    <body>
        <div class="map_wrap">
            <div id="map" style="width:100%;height:100%;position:relative;overflow:hidden;"></div>

            <div id="menu_wrap" class="bg_white">
                <div class="option">
                    <div>
                        <form onsubmit="searchPlaces(); return false;">
                            키워드 : <input type="text" value="제주도 서귀포시 맛집" id="keyword" size="15"> 
                            <button type="submit">검색하기</button> 
                        </form>
                    </div>
                </div>
                <hr>
                <ul id="placesList"></ul>
                <div id="pagination"></div>
            </div>
        </div>
        <p id="result"></p>
        <script type="text/javascript" src="//dapi.kakao.com/v2/maps/sdk.js?appkey=28e4d4739fe65a650ce5cb32cf39e00e&libraries=services"></script>
        <script>
            var markers = [];
            var mapContainer = document.getElementById('map');
            var mapOption = {
                center: new kakao.maps.LatLng(33.49962, 126.531188),
                level: 3
            };

            var map = new kakao.maps.Map(mapContainer, mapOption);
            var ps = new kakao.maps.services.Places();
            var infowindow = new kakao.maps.InfoWindow({zIndex:1});

            searchPlaces();

            function searchPlaces() {
                var keyword = document.getElementById('keyword').value;
                if (!keyword.replace(/^\s+|\s+$/g, '')) {
                    alert('키워드를 입력해주세요!');
                    return false;
                }
                ps.keywordSearch(keyword, placesSearchCB); 
            }

            function placesSearchCB(data, status, pagination) {
                if (status === kakao.maps.services.Status.OK) {
                    displayPlaces(data);
                    displayPagination(pagination);
                } else if (status === kakao.maps.services.Status.ZERO_RESULT) {
                    alert('검색 결과가 존재하지 않습니다.');
                } else if (status === kakao.maps.services.Status.ERROR) {
                    alert('검색 결과 중 오류가 발생했습니다.');
                }
            }

            function displayPlaces(places) {
                var listEl = document.getElementById('placesList'), 
                fragment = document.createDocumentFragment(),
                bounds = new kakao.maps.LatLngBounds();

                removeAllChildNods(listEl);
                removeMarker();
                
                for (var i=0; i<places.length; i++) {
                    var placePosition = new kakao.maps.LatLng(places[i].y, places[i].x),
                        marker = addMarker(placePosition, i), 
                        itemEl = getListItem(i, places[i]);

                    bounds.extend(placePosition);

                    (function(marker, title, lat, lng) {
                        kakao.maps.event.addListener(marker, 'mouseover', function() {
                            displayInfowindow(marker, title);
                        });

                        kakao.maps.event.addListener(marker, 'mouseout', function() {
                            infowindow.close();
                        });

                        itemEl.onclick = function() {
                            sendCoordinates(lat, lng);
                        };

                        itemEl.onmouseover = function () {
                            displayInfowindow(marker, title);
                        };

                        itemEl.onmouseout = function () {
                            infowindow.close();
                        };
                    })(marker, places[i].place_name, places[i].y, places[i].x);

                    fragment.appendChild(itemEl);
                }

                listEl.appendChild(fragment);
                map.setBounds(bounds);
            }

            // 검색 결과 목록을 클릭하면 해당 장소로 지도의 중심을 이동하도록 이벤트를 추가하는 코드
            function getListItem(index, places) {
                var el = document.createElement('li'),
                    itemStr = '<span class="markerbg marker_' + (index + 1) + '"></span>' +
                            '<div class="info">' +
                            '   <h5>' + places.place_name + '</h5>';

                if (places.road_address_name) {
                    itemStr += '    <span>' + places.road_address_name + '</span>' +
                            '   <span class="jibun gray">' + places.address_name + '</span>';
                } else {
                    itemStr += '    <span>' + places.address_name + '</span>';
                }

                itemStr += '  <span class="tel">' + places.phone + '</span>' +
                        '</div>';

                el.innerHTML = itemStr;
                el.className = 'item';

                // 검색 결과를 클릭했을 때 해당 위치로 지도 이동 및 중심 변경
                el.onclick = function() {
                    // 좌표 정보 확인
                    console.log('Moving to:', places.y, places.x);

                    var latLng = new kakao.maps.LatLng(parseFloat(places.y), parseFloat(places.x)); // 위도, 경도를 숫자로 변환
                    
                    // 지도의 중심을 클릭한 위치로 이동
                    map.setCenter(latLng);  
                    
                    // 기존 마커를 제거
                    removeMarker();

                    // 새 마커 생성 및 지도에 표시
                    var marker = new kakao.maps.Marker({
                        map: map,
                        position: latLng
                    });

                    // 마커 배열에 추가
                    markers.push(marker);
                };

                return el;
            }

            function addMarker(position, idx) {
                var imageSrc = 'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/marker_number_blue.png', 
                    imageSize = new kakao.maps.Size(36, 37),  
                    imgOptions = {
                        spriteSize: new kakao.maps.Size(36, 691),
                        spriteOrigin: new kakao.maps.Point(0, (idx*46)+10),
                        offset: new kakao.maps.Point(13, 37)
                    },
                    markerImage = new kakao.maps.MarkerImage(imageSrc, imageSize, imgOptions),
                    marker = new kakao.maps.Marker({
                        position: position, 
                        image: markerImage 
                    });

                marker.setMap(map); 
                markers.push(marker);  
                return marker;
            }

            function removeMarker() {
                for (var i = 0; i < markers.length; i++) {
                    markers[i].setMap(null);
                }   
                markers = [];
            }

            function displayInfowindow(marker, title) {
                var content = '<div style="padding:5px;z-index:1;">' + title + '</div>';
                infowindow.setContent(content);
                infowindow.open(map, marker);
            }

            function displayPagination(pagination) {
                var paginationEl = document.getElementById('pagination'),
                    fragment = document.createDocumentFragment(),
                    i;

                while (paginationEl.hasChildNodes()) {
                    paginationEl.removeChild(paginationEl.lastChild);
                }

                for (i = 1; i <= pagination.last; i++) {
                    var el = document.createElement('a');
                    el.href = "#";
                    el.innerHTML = i;

                    if (i === pagination.current) {
                        el.className = 'on';
                    } else {
                        el.onclick = (function(i) {
                            return function() {
                                pagination.gotoPage(i);
                            }
                        })(i);
                    }

                    fragment.appendChild(el);
                }
                paginationEl.appendChild(fragment);
            }

            function removeAllChildNods(el) {   
                while (el.hasChildNodes()) {
                    el.removeChild(el.lastChild);
                }
            }

            function sendCoordinates(lat, lng) {
                fetch('/click', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({latitude: lat, longitude: lng})
                })
                .then(response => response.text())
                .then(data => {
                    console.log('Server response:', data);
                    // 지도의 중심을 이동시킴
                    var latLng = new kakao.maps.LatLng(lat, lng);
                    map.setCenter(latLng);

                    // 기존 마커 제거 후 새로운 마커 추가
                    removeMarker();
                    var marker = new kakao.maps.Marker({
                        map: map,
                        position: latLng
                    });
                    markers.push(marker);
                })
                .catch((error) => {
                    console.error('Error:', error);
                });
            }
        </script>
    </body>
    </html>
    '''

@app.route('/click', methods=['POST'])
def handle_click():
    global latitude, longitude
    data = request.json
    latitude = data['latitude']
    longitude = data['longitude']
    return 'OK', 200

@app.route('/get_coordinates', methods=['GET'])
def get_coordinates():
    global latitude, longitude
    coords = {'latitude': latitude, 'longitude': longitude}
    
    latitude = None
    longitude = None
    return jsonify(coords)

if __name__ == '__main__':
    app.run(port=5000)