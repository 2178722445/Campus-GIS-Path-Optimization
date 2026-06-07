import os
import json
import geopandas as gpd
import networkx as nx
from shapely.geometry import Point, LineString, mapping

def run_dijkstra_path(start_lon, start_lat, end_lon, end_lat):
    # 获取脚本所在的当前文件夹绝对路径，确保读取数据不出错
    base_path = os.path.dirname(os.path.abspath(__file__))
    roads_path = os.path.join(base_path, '04_paths_or_roads.geojson')
    
    # 定义输出路径（保留保存文件的功能，方便QGIS查看）
    output_path = os.path.join(base_path, 'analysis_result_dijkstra.json')
    preview_path = os.path.join(base_path, 'dijkstra_preview.geojson')

    print(f"--- 启动 Dijkstra 最短路径分析 ---")

    # 1. 构建路网图 (米制坐标系)
    if not os.path.exists(roads_path):
        print(f"错误：找不到路网文件 {roads_path}")
        return []

    roads = gpd.read_file(roads_path).to_crs(epsg=3857)
    G = nx.Graph()
    for _, row in roads.iterrows():
        coords = list(row.geometry.coords)
        for i in range(len(coords) - 1):
            p1, p2 = coords[i], coords[i+1]
            dist = Point(p1).distance(Point(p2))
            # 注意：这里要指定 weight 为距离
            G.add_edge(p1, p2, weight=dist)

    # 2. 将起点终点投影到最近的路网节点
    def find_nearest_node(lon, lat):
        p_m = gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326").to_crs(epsg=3857)[0]
        nodes = list(G.nodes)
        nearest = min(nodes, key=lambda n: Point(n).distance(p_m))
        return nearest

    source_node = find_nearest_node(start_lon, start_lat)
    target_node = find_nearest_node(end_lon, end_lat)

    # 3. 计算最短路径
    print(f"正在执行从 ({start_lon}, {start_lat}) 到 ({end_lon}, {end_lat}) 的搜索...")
    try:
        # 这里的 weight 必须和上面 add_edge 里的名字对应
        path_nodes = nx.shortest_path(G, source=source_node, target=target_node, weight='weight')
        path_length = nx.shortest_path_length(G, source=source_node, target=target_node, weight='weight')
    except nx.NetworkXNoPath:
        print("错误：两点间无连通路径！")
        return []

    # 4. 构造路径几何体并转回经纬度
    path_line = LineString(path_nodes)
    path_gdf = gpd.GeoSeries([path_line], crs="EPSG:3857").to_crs(epsg=4326)
    
    # 5. 封装标准化结果
    walking_time = round(path_length / 72, 1) # 1.2m/s = 72m/min
    
    res_item = {
        "objectId": f"path_{start_lon}_{end_lon}",
        "value": round(path_length, 2), 
        "level": 2, 
        "label": "最短步行路径",
        "style": {
            "color": "#ff4500", 
            "width": 5,
            "opacity": 0.9
        },
        "description": f"全长 {round(path_length, 2)} 米，预计步行时长 {walking_time} 分钟",
        "geometry": mapping(path_gdf.iloc[0])
    }
    
    # 保存结果到文件
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump([res_item], f, ensure_ascii=False, indent=4)

    # 返回结果给 Flask 
    return [res_item]