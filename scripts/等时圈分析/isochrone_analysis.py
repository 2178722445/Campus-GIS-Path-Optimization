import os
import json
import geopandas as gpd
import networkx as nx
from shapely.geometry import Point, MultiPoint, mapping

def run_isochrone_analysis(target_id=None):
    """
    等时圈分析核心模块
    :param target_id: 可选，指定分析某个特定设施的ID。若为None则分析所有设施。
    :return: 标准化结果列表
    """
    # 1. 路径定位
    base_path = os.path.dirname(os.path.abspath(__file__))
    roads_path = os.path.join(base_path, '04_paths_or_roads.geojson')
    objects_path = os.path.join(base_path, '03_campus_objects.json')

    if not os.path.exists(roads_path) or not os.path.exists(objects_path):
        print(f"错误：在 {base_path} 找不到必要的数据文件。")
        return []

    # 2. 构建路网拓扑 (米制坐标系计算)
    roads = gpd.read_file(roads_path).to_crs(epsg=3857)
    G = nx.Graph()
    for _, row in roads.iterrows():
        coords = list(row.geometry.coords)
        for i in range(len(coords) - 1):
            p1, p2 = coords[i], coords[i+1]
            dist = Point(p1).distance(Point(p2))
            G.add_edge(p1, p2, weight=dist/1.2) # 步行速度1.2m/s

    # 3. 读取设施点
    with open(objects_path, 'r', encoding='utf-8') as f:
        facilities_data = json.load(f)
    
    features_list = facilities_data['features'] if 'features' in facilities_data else facilities_data

    # 4. 参数配置
    time_limits = [300, 600, 900] 
    styles = {
        300: {"color": "#28a745", "opacity": 0.6}, # 绿色 (5min)
        600: {"color": "#ffc107", "opacity": 0.5}, # 黄色 (10min)
        900: {"color": "#dc3545", "opacity": 0.4}  # 红色 (15min)
    }

    results = []
    nodes_list = list(G.nodes)

    # 5. 执行循环分析
    for feat in features_list:
        # 获取ID和名称
        props = feat.get('properties', feat)
        obj_id = props.get('objectId', 'unknown')
        obj_name = props.get('name', '未命名设施')

        # 如果指定了分析某个ID，不匹配的跳过
        if target_id and obj_id != target_id:
            continue

        # 获取经纬度并转为米制坐标
        geom = feat.get('geometry', {})
        lon, lat = geom.get('coordinates', [0,0])
        p_m = gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326").to_crs(epsg=3857)[0]
        
        # 寻找路网最近点
        source_node = min(nodes_list, key=lambda n: Point(n).distance(p_m))

        for idx, t in enumerate(time_limits):
            # Dijkstra 算法搜索
            subgraph_nodes = nx.single_source_dijkstra_path_length(G, source_node, cutoff=t, weight='weight')
            
            if len(subgraph_nodes) < 3: continue
            
            # 生成几何体 (凸包)
            hull = MultiPoint(list(subgraph_nodes.keys())).convex_hull
            # 计算面积 (扩展字段)
            area_sqm = round(hull.area, 2)
            
            # 转回经纬度
            hull_gdf = gpd.GeoSeries([hull], crs="EPSG:3857").to_crs(epsg=4326)
            
            # 字段封装
            res_item = {
                "objectId": obj_id,   
                "value": t,                  # 时间阈值
                "level": idx + 1,            # 1/2/3级
                "label": f"{t//60}分钟服务圈",
                "style": styles[t],          #含颜色和透明度
                "description": f"从{obj_name}出发步行{t//60}分钟可达范围", 
                "geometry": mapping(hull_gdf.iloc[0]), # GeoJSON格式
                #  扩展字段 
                "area_sqm": area_sqm,        # 覆盖面积
                "reachable_nodes": len(subgraph_nodes) # 覆盖路网节点数
            }
            results.append(res_item)
    print(f"设施 {obj_id} 分析完成")

    # --- 7. 保存最终结果 (集成用) ---
    output_filename = os.path.join(base_path, 'analysis_result_isochrone.json')
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    # 8. 生成 QGIS 预览文件
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

    preview_filename = os.path.join(base_path, 'qgis_preview.geojson')
    with open(preview_filename, 'w', encoding='utf-8') as f:
        json.dump(preview_geojson, f, ensure_ascii=False, indent=4)
    
    print(f"\n标准化分析完成！")
    print(f"1. 集成文件已生成: {output_filename}")
    print(f"2. QGIS预览文件已生成: {preview_filename}")
    
    return results # 注意这里是 results，不是 res

if __name__ == "__main__":
    data = run_isochrone_analysis()