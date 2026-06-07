import os
import sys
import json
from flask import Flask, jsonify, request
from flask_cors import CORS

# 1.自动处理所有子文件夹的导入
current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_path = os.path.join(current_dir, 'scripts')

# 3. 把scripts文件夹及其内部的子文件夹加入搜索路径
if os.path.exists(scripts_path):
    sys.path.append(scripts_path)
    
    sub_folders = [
        "等时圈分析",
        "Dijkstra 最短路径分析",
        "KNN",
        "blind_spot_analysis",
        "食堂服务分区（Voronoi)"
    ]

    for folder in sub_folders:
        folder_path = os.path.join(scripts_path, folder)
        if os.path.exists(folder_path):
            sys.path.append(folder_path)
            print(f"已加载路径: {folder}")
        else:
            print(f"找不到文件夹: {folder_path}")
else:
    print(f"找不到 scripts 文件夹，请检查目录结构！")


# 2. 导入所有个算法模块 
from isochrone_analysis import run_isochrone_analysis
from dijkstra_path_analysis import run_dijkstra_path
from knn_search_analysis import run_knn_search
from blind_spot_analysis import identify_blind_spots  # 盲区
from voronoi_analysis import run_voronoi_analysis      # 维诺图

app = Flask(__name__)
CORS(app)

# 1. 路径规划接口
@app.route('/api/analysis/path')
def get_path():
    result = run_dijkstra_path(103.720, 36.110, 103.725, 36.105)
    return jsonify(result)

# 2. KNN 接口
@app.route('/api/analysis/knn')
def get_knn():
    result = run_knn_search(103.722, 36.108, k=3)
    return jsonify(result)

# 3. 等时圈接口
@app.route('/api/analysis/isochrone')
def get_isochrone():
    try:
        # 直接调用导入的函数，获取实时的计算结果
        result = run_isochrone_analysis() 
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 4. 盲区识别接口 
@app.route('/api/analysis/blind_spot')
def get_blind_spot():
    # 调用 identify_blind_spots 函数
    result = identify_blind_spots() 
    return jsonify(result)

# 5. voronoi图分区接口 
@app.route('/api/analysis/voronoi')
def get_voronoi():
    # 调用 run_voronoi_analysis 函数
    result = run_voronoi_analysis()
    return jsonify(result)

if __name__ == '__main__':
    print("第七组 GIS分析服务启动")
    print("1. 路径: /api/analysis/path")
    print("2. KNN: /api/analysis/knn")
    print("3. 等时圈: /api/analysis/isochrone")
    print("4. 盲区: /api/analysis/blind_spot")
    print("5. 维诺图: /api/analysis/voronoi") 
    app.run(debug=True, port=5000)