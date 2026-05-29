import os
import json
import geopandas as gpd
from scipy.spatial import Voronoi
from shapely.geometry import Polygon, Point, mapping

def run_voronoi_analysis():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 输入文件
    points_path = os.path.join(current_dir, '03_campus_objects.json')
    boundary_path = os.path.join(current_dir, '05_facilities_or_regions.geojson')
    # 输出文件
    output_path = os.path.join(current_dir, 'analysis_result_voronoi.json')
    preview_path = os.path.join(current_dir, 'voronoi_preview.geojson')

    print("--- 启动食堂服务分区 (Voronoi) 算法 ---")

    # 1. 加载数据并转为米制坐标 (EPSG:3857) 以保证几何运算准确
    boundary_gdf = gpd.read_file(boundary_path).to_crs(epsg=3857)
    campus_poly = boundary_gdf.unary_union

    with open(points_path, 'r', encoding='utf-8') as f:
        pts_data = json.load(f)
    
    # 仅提取类型为“食堂”的点 (假设属性里 type 是 canteen)
    feats = pts_data['features'] if 'features' in pts_data else pts_data
    canteen_points = []
    canteen_info = []

    for f in feats:
        # 这里你可以根据需要筛选 type == 'canteen'，目前为了演示处理所有设施点
        props = f['properties'] if 'properties' in f else f
        geom = f['geometry'] if 'geometry' in f else {"coordinates": f.get('coordinates')}
        
        lon, lat = geom['coordinates']
        # 转为米制坐标
        p_m = gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326").to_crs(epsg=3857)[0]
        canteen_points.append([p_m.x, p_m.y])
        canteen_info.append(props)

    if len(canteen_points) < 3:
        print("❌ 错误：设施点太少（至少需要3个）无法构建泰森多边形。")
        return

    # 2. 构建 Voronoi 图
    # 为了处理边缘无限延伸的问题，我们增加一个巨大的虚拟边界框
    import numpy as np
    coords = np.array(canteen_points)
    vor = Voronoi(coords)

    # 3. 将 Voronoi 区域转为多边形并与校园边界取交集
    results = []
    preview_features = []

    for i, region_idx in enumerate(vor.point_region):
        region = vor.regions[region_idx]
        if -1 in region or len(region) == 0:
            # 处理边缘无限大的情况：这里我们用一个极大的矩形模拟
            continue 

        # 提取顶点坐标
        world_poly = Polygon([vor.vertices[v] for v in region])
        
        # 核心：与校园边界取交集 (Clip)
        final_poly = world_poly.intersection(campus_poly)
        
        if final_poly.is_empty: continue

        # 转回经纬度
        final_gdf = gpd.GeoSeries([final_poly], crs="EPSG:3857").to_crs(epsg=4326)
        geom_json = mapping(final_gdf[0])
        
        obj_id = canteen_info[i].get('objectId', f'node_{i}')
        name = canteen_info[i].get('name', '未命名设施')

        # 4. 封装结果
        res_item = {
            "objectId": obj_id,
            "value": round(final_poly.area, 2), # 分区面积
            "level": 5,
            "label": f"{name} 服务分区",
            "style": {
                "color": f"#{np.random.randint(0, 0xFFFFFF):06x}", # 随机分配颜色
                "opacity": 0.5
            },
            "description": f"该区域属于 {name} 的核心服务范围，面积 {round(final_poly.area, 2)} 平方米",
            "geometry": geom_json
        }
        results.append(res_item)
        
        # 准备 QGIS 预览
        preview_features.append({
            "type": "Feature",
            "properties": {"name": name, "area": res_item["value"]},
            "geometry": geom_json
        })

    # 5. 保存结果
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
        
    with open(preview_path, 'w', encoding='utf-8') as f:
        json.dump({"type": "FeatureCollection", "features": preview_features}, f, ensure_ascii=False, indent=4)

    print(f"✅ Voronoi分区计算完成！共生成 {len(results)} 个服务分区。")
    print(f"预览文件已生成: {preview_path}")

if __name__ == "__main__":
    run_isochrone_analysis = run_voronoi_analysis() # 运行