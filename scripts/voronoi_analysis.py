import os
import json
import geopandas as gpd
import numpy as np
from scipy.spatial import Voronoi
from shapely.geometry import Polygon, Point, mapping

from data_config import get_objects_path, get_polygons_path, get_data_dir


def run_voronoi_analysis(data_dir=None):
    data_dir = get_data_dir(data_dir)
    points_path = get_objects_path(data_dir)
    boundary_path = get_polygons_path(data_dir)

    print("--- 启动 Voronoi 分析 ---")

    if not os.path.exists(points_path):
        print(f"错误：找不到设施文件 {points_path}")
        return []

    if not os.path.exists(boundary_path):
        print(f"错误：找不到边界文件 {boundary_path}")
        return []

    try:
        boundary_gdf = gpd.read_file(boundary_path)
        if boundary_gdf.crs is None:
            boundary_gdf.set_crs(epsg=4326, inplace=True)
        campus_poly = boundary_gdf.to_crs(epsg=3857).unary_union

        with open(points_path, 'r', encoding='utf-8') as f:
            pts_data = json.load(f)

        feats = pts_data['features'] if 'features' in pts_data else pts_data
        coords_m = []
        infos = []

        for f in feats:
            geom = f.get('geometry', f)
            lon, lat = geom.get('coordinates', [0, 0])
            p_m = gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326").to_crs(epsg=3857)[0]
            coords_m.append([p_m.x, p_m.y])
            infos.append(f.get('properties', f))

        if len(coords_m) < 3:
            print("错误：点位数量不足3个，无法生成泰森多边形。")
            return []

        coords_np = np.array(coords_m)
        vor = Voronoi(coords_np)

        results = []
        for i, reg_idx in enumerate(vor.point_region):
            region = vor.regions[reg_idx]
            if -1 in region or not region:
                continue

            world_poly = Polygon([vor.vertices[v] for v in region])
            final_poly = world_poly.intersection(campus_poly)

            if final_poly.is_empty:
                continue

            poly_4326 = gpd.GeoSeries([final_poly], crs="EPSG:3857").to_crs(epsg=4326)

            props = infos[i]
            obj_id = props.get('objectId') or f"node_{i}"
            name = props.get('name') or obj_id

            results.append({
                "objectId": obj_id,
                "value": round(final_poly.area, 1),
                "level": 5,
                "label": f"{name} 服务区",
                "style": {
                    "color": f"#{np.random.randint(0, 0xFFFFFF):06x}",
                    "opacity": 0.4
                },
                "geometry": mapping(poly_4326[0])
            })

        out_file = os.path.join(data_dir, 'analysis_result_voronoi.json')
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)

        print(f"Voronoi 分区计算成功，生成 {len(results)} 个结果。")
        return results

    except Exception as e:
        print(f"Voronoi 模块崩溃: {e}")
        return []


if __name__ == "__main__":
    run_voronoi_analysis()