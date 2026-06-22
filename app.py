import os
import sys
import json
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

root_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.join(root_dir, 'scripts')
data_dir = os.path.join(root_dir, 'data')

sys.path.insert(0, scripts_dir)

from data_config import get_roads_path, get_objects_path, get_polygons_path, data_ready
from isochrone_analysis import run_isochrone_analysis
from dijkstra_path_analysis import run_dijkstra_path
from knn_search_analysis import run_knn_search

app = Flask(__name__, static_folder=root_dir, static_url_path='')
CORS(app)
os.makedirs(data_dir, exist_ok=True)


def _load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _count_features(data):
    if isinstance(data, dict) and 'features' in data:
        return len(data['features'])
    if isinstance(data, list):
        return len(data)
    return 0


def _data_bounds(facilities, roads, polygons=None):
    lons, lats = [], []
    for src in (facilities, roads, polygons):
        if not src or 'features' not in src:
            continue
        for feat in src['features']:
            geom = feat.get('geometry', {})
            coords = geom.get('coordinates', [])
            if geom.get('type') == 'Point' and len(coords) >= 2:
                lons.append(coords[0])
                lats.append(coords[1])
            elif geom.get('type') == 'LineString':
                for c in coords:
                    lons.append(c[0])
                    lats.append(c[1])
            elif geom.get('type') == 'Polygon':
                for ring in coords:
                    for c in ring:
                        lons.append(c[0])
                        lats.append(c[1])
            elif geom.get('type') == 'MultiPolygon':
                for poly in coords:
                    for ring in poly:
                        for c in ring:
                            lons.append(c[0])
                            lats.append(c[1])
    if not lons:
        return None
    return {
        'west': min(lons), 'east': max(lons),
        'south': min(lats), 'north': max(lats),
        'centerLon': (min(lons) + max(lons)) / 2,
        'centerLat': (min(lats) + max(lats)) / 2,
    }


@app.route('/')
def index():
    return send_from_directory(root_dir, 'index.html')


@app.route('/api/health')
def api_health():
    return jsonify({'ok': True, 'message': 'backend running'})


@app.route('/api/data/status')
def api_data_status():
    roads_path = get_roads_path()
    objects_path = get_objects_path()
    polygons_path = get_polygons_path()
    status = {
        'ready': data_ready(),
        'facilities': os.path.exists(objects_path),
        'roads': os.path.exists(roads_path),
        'polygons': os.path.exists(polygons_path),
        'facilityCount': 0,
        'roadCount': 0,
        'polygonCount': 0,
        'bounds': None,
    }
    facilities = roads = polygons = None
    if status['facilities']:
        facilities = _load_json(objects_path)
        status['facilityCount'] = _count_features(facilities)
    if status['roads']:
        roads = _load_json(roads_path)
        status['roadCount'] = _count_features(roads)
    if status['polygons']:
        polygons = _load_json(polygons_path)
        status['polygonCount'] = _count_features(polygons)
    status['bounds'] = _data_bounds(facilities, roads, polygons)
    return jsonify(status)


@app.route('/api/data/preview')
def api_data_preview():
    result = {'facilities': None, 'roads': None, 'polygons': None}
    objects_path = get_objects_path()
    roads_path = get_roads_path()
    polygons_path = get_polygons_path()
    if os.path.exists(objects_path):
        result['facilities'] = _load_json(objects_path)
    if os.path.exists(roads_path):
        result['roads'] = _load_json(roads_path)
    if os.path.exists(polygons_path):
        result['polygons'] = _load_json(polygons_path)
    return jsonify(result)


@app.route('/api/data/upload', methods=['POST'])
def api_data_upload():
    saved = []
    errors = []

    if 'facilities' in request.files:
        file = request.files['facilities']
        if file.filename:
            try:
                content = json.load(file.stream)
                if 'features' not in content and not isinstance(content, list):
                    errors.append('设施数据格式无效，需为 GeoJSON FeatureCollection')
                else:
                    path = get_objects_path()
                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump(content, f, ensure_ascii=False, indent=2)
                    saved.append('facilities')
            except json.JSONDecodeError:
                errors.append('设施文件不是有效的 JSON')

    if 'roads' in request.files:
        file = request.files['roads']
        if file.filename:
            try:
                content = json.load(file.stream)
                if 'features' not in content:
                    errors.append('路网数据格式无效，需为 GeoJSON FeatureCollection')
                else:
                    path = get_roads_path()
                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump(content, f, ensure_ascii=False, indent=2)
                    saved.append('roads')
            except json.JSONDecodeError:
                errors.append('路网文件不是有效的 JSON/GeoJSON')

    if 'polygons' in request.files:
        file = request.files['polygons']
        if file.filename:
            try:
                content = json.load(file.stream)
                if 'features' not in content:
                    errors.append('面数据格式无效，需为 GeoJSON FeatureCollection')
                else:
                    path = get_polygons_path()
                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump(content, f, ensure_ascii=False, indent=2)
                    saved.append('polygons')
            except json.JSONDecodeError:
                errors.append('面数据文件不是有效的 JSON/GeoJSON')

    if errors:
        return jsonify({'ok': False, 'errors': errors, 'saved': saved}), 400

    if not saved:
        return jsonify({'ok': False, 'errors': ['未选择任何文件']}), 400

    return jsonify({'ok': True, 'saved': saved, 'ready': data_ready()})


@app.route('/api/analysis/isochrone')
def api_isochrone():
    if not os.path.exists(get_roads_path()):
        return jsonify({'ok': False, 'error': '请先导入路网数据', 'data': []}), 400

    lon = request.args.get('lon', type=float)
    lat = request.args.get('lat', type=float)
    if lon is None or lat is None:
        return jsonify({'ok': False, 'error': '请在地图上选择等时圈中心点', 'data': []}), 400

    try:
        data = run_isochrone_analysis(center_lon=lon, center_lat=lat)
        return jsonify({'ok': True, 'data': data})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'data': []}), 500


@app.route('/api/analysis/path')
def api_path():
    if not os.path.exists(get_roads_path()):
        return jsonify({'ok': False, 'error': '请先导入路网数据', 'data': []}), 400

    slon = request.args.get('slon', type=float)
    slat = request.args.get('slat', type=float)
    elon = request.args.get('elon', type=float)
    elat = request.args.get('elat', type=float)
    if None in (slon, slat, elon, elat):
        return jsonify({'ok': False, 'error': '请在地图上选择起点和终点', 'data': []}), 400

    try:
        data = run_dijkstra_path(slon, slat, elon, elat)
        if not data:
            return jsonify({'ok': False, 'error': '未找到连通路径，请检查路网或点位', 'data': []})
        return jsonify({'ok': True, 'data': data})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'data': []}), 500


@app.route('/api/analysis/knn')
def api_knn():
    if not os.path.exists(get_objects_path()):
        return jsonify({'ok': False, 'error': '请先导入设施数据', 'data': []}), 400

    lon = request.args.get('lon', type=float)
    lat = request.args.get('lat', type=float)
    if lon is None or lat is None:
        return jsonify({'ok': False, 'error': '请在地图上选择查询点', 'data': []}), 400

    try:
        data = run_knn_search(lon, lat, k=1)
        if not data:
            return jsonify({'ok': False, 'error': '未找到最近设施', 'data': []})
        return jsonify({'ok': True, 'data': data})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'data': []}), 500


@app.route('/api/analysis/blind_spot')
def api_blind_spot():
    if not os.path.exists(get_roads_path()):
        return jsonify({'ok': False, 'error': '请先导入路网数据', 'data': []}), 400

    try:
        from blind_spot_analysis import identify_blind_spots
        data = identify_blind_spots(data_dir=data_dir)
        if not data:
            return jsonify({'ok': False, 'error': '未检测到盲区，请先运行等时圈分析', 'data': []})
        return jsonify({'ok': True, 'data': data})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'data': []}), 500


@app.route('/api/analysis/voronoi')
def api_voronoi():
    if not os.path.exists(get_objects_path()):
        return jsonify({'ok': False, 'error': '请先导入设施数据', 'data': []}), 400

    try:
        from voronoi_analysis import run_voronoi_analysis
        data = run_voronoi_analysis(data_dir=data_dir)
        if not data:
            return jsonify({'ok': False, 'error': 'Voronoi 分析失败，请检查设施点数量和边界数据', 'data': []})
        return jsonify({'ok': True, 'data': data})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'data': []}), 500


if __name__ == '__main__':
    print('\n智慧校园 GIS 分析系统')
    print('访问地址: http://127.0.0.1:5000')
    app.run(debug=True, host='127.0.0.1', port=5000)