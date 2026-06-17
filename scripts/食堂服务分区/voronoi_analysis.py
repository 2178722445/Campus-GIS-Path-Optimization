import os
import json
import geopandas as gpd
import numpy as np
from scipy.spatial import Voronoi
from shapely.geometry import Polygon, Point, mapping

def run_voronoi_analysis():
    # 1. 路径自动定位
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(current_dir))
    
    # 尝试读取数据（优先找 data 文件夹，找不到就找当前文件夹）
    points_path = os.path.join(root_dir, 'data', '03_campus_objects.json')
    boundary_path = os.path.join(root_dir, 'data', '05_facilities_or_regions.geojson')
    
    if not os.path.exists(points_path):
        points_path = os.path.join(current_dir, '03_campus_objects.json')
    if not os.path.exists(boundary_path):
        boundary_path = os.path.join(current_dir, '05_facilities_or_regions.geojson')

    print("--- 启动 Voronoi 分析 ---")

    try:
        # 2. 读取边界并转为米制坐标
        boundary_gdf = gpd.read_file(boundary_path)
        if boundary_gdf.crs is None: boundary_gdf.set_crs(epsg=4326, inplace=True)
        campus_poly = boundary_gdf.to_crs(epsg=3857).unary_union

        # 3. 读取设施点
        with open(points_path, 'r', encoding='utf-8') as f:
            pts_data = json.load(f)
        
        feats = pts_data['features'] if 'features' in pts_data else pts_data
        coords_m = []
        infos = []

        for f in feats:
            geom = f.get('geometry', f)
            lon, lat = geom.get('coordinates', [0,0])
            p_m = gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326").to_crs(epsg=3857)[0]
            coords_m.append([p_m.x, p_m.y])
            infos.append(f.get('properties', f))

        if len(coords_m) < 3:
            print("⚠️ 错误：点位数量不足3个，无法生成泰森多边形。")
            return []

        # 4. 生成 Voronoi 拓扑
        coords_np = np.array(coords_m)
        vor = Voronoi(coords_np)

        results = []
        # 5. 分区裁切与坐标转回 (关键步骤)
        for i, reg_idx in enumerate(vor.point_region):
            region = vor.regions[reg_idx]
            if -1 in region or not region: continue
            
            world_poly = Polygon([vor.vertices[v] for v in region])
            final_poly = world_poly.intersection(campus_poly) # 裁切
            
            if final_poly.is_empty: continue
            
            # 【核心修复】必须转回经纬度 4326，否则 Cesium 看不见
            poly_4326 = gpd.GeoSeries([final_poly], crs="EPSG:3857").to_crs(epsg=4326)
            
            props = infos[i]
            obj_id = props.get('objectId') or f"node_{i}"
            # 解决 None 标签问题
            name = props.get('name') or obj_id

            results.append({
                "objectId": obj_id,
                "value": round(final_poly.area, 1),
                "level": 5,
                "label": f"{name} 服务区",
                "style": {
                    "color": f"#{np.random.randint(0, 0xFFFFFF):06x}", # 随机鲜艳颜色
                    "opacity": 0.4
                },
                "geometry": mapping(poly_4326[0])
            })

        # 保存 JSON
        out_file = os.path.join(current_dir, 'analysis_result_voronoi.json')
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        
        print(f"✅ Voronoi 分区计算成功，生成 {len(results)} 个结果。")
        return results

    except Exception as e:
        print(f"❌ Voronoi 模块崩溃: {e}")
        return []

if __name__ == "__main__":
    run_voronoi_analysis()