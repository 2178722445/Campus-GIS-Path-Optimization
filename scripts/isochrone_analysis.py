import os
import geopandas as gpd
import networkx as nx
import json
from shapely.geometry import Point, MultiPoint, mapping

# 设置运行环境
current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)

def run_isochrone_analysis():
    # 1. 读取路网数据
    print("正在加载路网数据...")
    roads = gpd.read_file('04_paths_or_roads.geojson')
    # 转为米制坐标 EPSG:3857，方便计算真实距离
    roads = roads.to_crs(epsg=3857)
    
    # 2. 构建路网模型 (Graph)
    G = nx.Graph()
    print("正在构建路网拓扑结构...")
    for _, row in roads.iterrows():
        coords = list(row.geometry.coords)
        for i in range(len(coords) - 1):
            p1, p2 = coords[i], coords[i+1]
            dist = Point(p1).distance(Point(p2))
            # 权重 = 通行时间 (秒) = 距离 / 步行速度(1.2m/s)
            weight = dist / 1.2 
            G.add_edge(p1, p2, weight=weight)

    # 3. 读取设施点数据
    with open('03_campus_objects.json', 'r', encoding='utf-8') as f:
        facilities_data = json.load(f)

    # 4. 等时圈分析参数 (5, 10, 15分钟)
    time_limits = [300, 600, 900] 
    # 样式配置（颜色对应等级）
    styles = {
        300: {"color": "#28a745", "opacity": 0.6}, # 绿色
        600: {"color": "#ffc107", "opacity": 0.5}, # 黄色
        900: {"color": "#dc3545", "opacity": 0.4}  # 红色
    }

    results = []

    # 5. 处理设施点列表
    if isinstance(facilities_data, dict) and 'features' in facilities_data:
        features_list = facilities_data['features']
    else:
        features_list = facilities_data 

    print(f"检测到 {len(features_list)} 个设施点，开始执行空间分析...")

    # 获取路网所有节点坐标，用于查找最近点
    nodes_list = list(G.nodes)
    
    for feat in features_list:
        # 获取 objectId
        if 'properties' in feat:
            obj_id = feat['properties'].get('objectId', 'unknown')
        else:
            obj_id = feat.get('objectId', 'unknown')

        # 获取坐标 (lon, lat)
        if 'geometry' in feat:
            lon, lat = feat['geometry']['coordinates']
        else:
            lon, lat = feat.get('coordinates', [0, 0]) 

        # --- 核心逻辑开始：计算等时圈 ---
        
        # 将设施点经纬度转为米制坐标
        point_geom = gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326").to_crs(epsg=3857)
        center_coords = (point_geom.iloc[0].x, point_geom.iloc[0].y)

        # 在路网图中找到距离设施点最近的节点
        try:
            source_node = min(nodes_list, key=lambda n: Point(n).distance(Point(center_coords)))
        except:
            print(f"⚠️ 设施 {obj_id} 附近找不到路网，跳过。")
            continue

        for idx, t in enumerate(time_limits):
            # 使用 Dijkstra 算法计算可达范围
            subgraph_nodes = nx.single_source_dijkstra_path_length(G, source_node, cutoff=t, weight='weight')
            
            # 调试信息：输出每个圈搜到了多少点
            # print(f"DEBUG: {obj_id} - {t}s 搜到节点: {len(subgraph_nodes)}")

            if len(subgraph_nodes) < 3:
                continue # 节点太少无法围成面
            
            # 生成多边形 (凸包)
            pts = MultiPoint(list(subgraph_nodes.keys()))
            hull = pts.convex_hull
            
            # 将生成的几何体转回经纬度坐标系
            hull_gdf = gpd.GeoSeries([hull], crs="EPSG:3857").to_crs(epsg=4326)
            
            # 构造任务要求的 JSON 格式
            res_item = {
                "objectId": obj_id,
                "value": t,
                "level": idx + 1,
                "label": f"{t//60}分钟服务圈",
                "style": styles[t],
                "description": f"设施 {obj_id} 步行 {t//60} 分钟可达区域",
                "geometry": mapping(hull_gdf.iloc[0]) 
            }
            results.append(res_item)
        
        print(f"设施 {obj_id} 分析完成")

    # 7. 保存最终结果
    output_filename = 'analysis_result_isochrone.json'
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    preview_geojson = {
        "type": "FeatureCollection",
        "features": []
    }
    for item in results:
        feature = {
            "type": "Feature",
            "properties": {
                "objectId": item["objectId"],
                "level": item["level"],
                "label": item["label"]
            },
            "geometry": item["geometry"]
        }
        preview_geojson["features"].append(feature)

    with open('qgis_preview.geojson', 'w', encoding='utf-8') as f:
        json.dump(preview_geojson, f, ensure_ascii=False, indent=4)
    
    print("✅ 已额外生成 QGIS 预览文件: qgis_preview.geojson")
    print(f"\n全部任务完成！")
    print(f"结果已保存至: {os.path.abspath(output_filename)}")
    print(f"总计生成分析要素: {len(results)} 个")

if __name__ == "__main__":
    run_isochrone_analysis()