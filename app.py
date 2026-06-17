import os
import sys
import json
from flask import Flask, jsonify, request
from flask_cors import CORS

# --- 1
root_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.join(root_dir, 'scripts')

if os.path.exists(scripts_dir):
    sys.path.append(scripts_dir)
    for root, dirs, files in os.walk(scripts_dir):
        for d in dirs:
            full_path = os.path.join(root, d)
            sys.path.append(full_path)
            print(f" 强行挂载路径: {d}")

# --- 2. 导入所有函数  ---
try:
    from isochrone_analysis import run_isochrone_analysis
    from dijkstra_path_analysis import run_dijkstra_path
    from knn_search_analysis import run_knn_search
    from blind_spot_analysis import identify_blind_spots
    from voronoi_analysis import run_voronoi_analysis
except ImportError as e:
    print(f" 模块导入失败，请检查脚本里的函数名: {e}")

app = Flask(__name__)
CORS(app)

# --- 3. 统一路由入口 ---

@app.route('/api/analysis/isochrone')
def api_iso():
    print(" 收到请求: 等时圈分析")
    return jsonify(run_isochrone_analysis())

@app.route('/api/analysis/path')
def api_path():
    print(" 收到请求: 路径规划")
    return jsonify(run_dijkstra_path(103.720, 36.110, 103.725, 36.105))

@app.route('/api/analysis/knn')
def api_knn():
    print(" 收到请求: 最近邻查询")
    return jsonify(run_knn_search(103.722, 36.108))

@app.route('/api/analysis/blind_spot')
def api_blind():
    print(" 收到请求: 盲区识别")
    try:
        res = identify_blind_spots()
        return jsonify(res)
    except Exception as e:
        print(f" 盲区执行报错: {e}")
        return jsonify([])

@app.route('/api/analysis/voronoi')
def api_vor():
    print(" 收到请求: 服务分区")
    try:
        res = run_voronoi_analysis()
        return jsonify(res)
    except Exception as e:
        print(f" 维诺图执行报错: {e}")
        return jsonify([])

if __name__ == '__main__':
    print("\n后端引擎启动，请在浏览器测试按钮。")
    app.run(debug=True, host='127.0.0.1', port=5000)
