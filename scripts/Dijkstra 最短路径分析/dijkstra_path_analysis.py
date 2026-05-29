import os
import json
import geopandas as gpd
import networkx as nx
from shapely.geometry import Point, LineString, mapping

def run_dijkstra_path(start_lon, start_lat, end_lon, end_lat):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    roads_path = os.path.join(current_dir, '04_paths_or_roads.geojson')
    output_path = os.path.join(current_dir, 'analysis_result_dijkstra.json')
    preview_path = os.path.join(current_dir, 'dijkstra_preview.geojson')

    print("--- 启动 Dijkstra 最短路径分析 ---")

    # 1. 构建路网图 (米制坐标系)
    roads = gpd.read_file(roads_path).to_crs(epsg=3857)
    G = nx.Graph()
    for _, row in roads.iterrows():
        coords = list(row.geometry.coords)
        for i in range(len(coords) - 1):
            p1, p2 = coords[i], coords[i+1]
            # 权重为物理长度
            dist = Point(p1).distance(Point(p2))
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
    print("正在执行 Dijkstra 搜索...")
    try:
        path_nodes = nx.shortest_path(G, source=source_node, target=target_node, weight='weight')
        path_length = nx.shortest_path_length(G, source=source_node, target=target_node, weight='weight')
    except nx.NetworkXNoPath:
        print("❌ 错误：两点间无连通路径，请检查路网拓扑！")
        return

    # 4. 构造路径几何体
    path_line = LineString(path_nodes)
    # 转回经纬度
    path_gdf = gpd.GeoSeries([path_line], crs="EPSG:3857").to_crs(epsg=4326)
    
    # 5. 封装符合任务要求的结果
    walking_time = round(path_length / 72, 1) # 1.2m/s = 72m/min
    
    res_item = {
        "objectId": f"path_{start_lon}_{end_lon}",
        "value": round(path_length, 2), # 路径长度
        "level": 2, # 路径分析级别
        "label": "最短步行路径",
        "style": {
            "color": "#ff4500", # 橙红色，醒目
            "width": 5,
            "opacity": 0.9
        },
        "description": f"全长 {round(path_length, 2)} 米，预计步行时长 {walking_time} 分钟",
        "geometry": mapping(path_gdf[0])
    }
    
    # 保存结果
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump([res_item], f, ensure_ascii=False, indent=4)

    # 生成 QGIS 预览
    preview_geojson = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": "最短路径", "length": path_length, "time": walking_time},
            "geometry": mapping(path_gdf[0])
        }]
    }
    with open(preview_path, 'w', encoding='utf-8') as f:
        json.dump(preview_geojson, f, ensure_ascii=False, indent=4)

    print(f"✅ 路径分析完成！总长: {round(path_length, 2)}m")
    print(f"预览文件已生成: {preview_path}")

if __name__ == "__main__":
    # 请根据你 QGIS 里画的校园路网，随机取两点的坐标测试
    # 示例：兰州交大某两点
    run_dijkstra_path(103.720, 36.110, 103.725, 36.105)