import os
import json
import geopandas as gpd
import networkx as nx
from shapely.geometry import Point, MultiPoint, mapping

from data_config import get_roads_path, get_objects_path, get_data_dir


def _build_road_graph(roads_path):
    roads = gpd.read_file(roads_path)
    if roads.crs is None:
        roads.set_crs(epsg=4326, inplace=True)
    roads = roads.to_crs(epsg=3857)

    graph = nx.Graph()
    for _, row in roads.iterrows():
        coords = list(row.geometry.coords)
        for i in range(len(coords) - 1):
            p1, p2 = coords[i], coords[i + 1]
            dist = Point(p1).distance(Point(p2))
            graph.add_edge(p1, p2, weight=dist / 1.2)
    return graph


def _isochrone_from_node(graph, source_node, obj_id, obj_name, time_limits, styles):
    nodes_list = list(graph.nodes)
    results = []

    for idx, t in enumerate(time_limits):
        subgraph_nodes = nx.single_source_dijkstra_path_length(
            graph, source_node, cutoff=t, weight='weight'
        )
        if len(subgraph_nodes) < 3:
            continue

        hull = MultiPoint(list(subgraph_nodes.keys())).convex_hull
        hull_gdf = gpd.GeoSeries([hull], crs="EPSG:3857").to_crs(epsg=4326)

        results.append({
            "objectId": obj_id,
            "value": t,
            "level": idx + 1,
            "label": f"{obj_name} {t // 60}分钟服务圈",
            "style": styles[t],
            "description": f"从 {obj_name} 出发步行 {t // 60} 分钟可达范围",
            "geometry": mapping(hull_gdf.iloc[0]),
        })
    return results


def run_isochrone_analysis(center_lon=None, center_lat=None, target_id=None, data_dir=None):
    data_dir = get_data_dir(data_dir)
    roads_path = get_roads_path(data_dir)
    objects_path = get_objects_path(data_dir)

    if not os.path.exists(roads_path):
        print(f"错误：找不到路网文件 {roads_path}")
        return []

    time_limits = [300, 600, 900]
    styles = {
        300: {"color": "#22c55e", "opacity": 0.55},
        600: {"color": "#eab308", "opacity": 0.45},
        900: {"color": "#ef4444", "opacity": 0.35},
    }

    graph = _build_road_graph(roads_path)
    nodes_list = list(graph.nodes)
    results = []

    if center_lon is not None and center_lat is not None:
        point_m = gpd.GeoSeries([Point(center_lon, center_lat)], crs="EPSG:4326").to_crs(epsg=3857)[0]
        source_node = min(nodes_list, key=lambda n: Point(n).distance(point_m))
        results = _isochrone_from_node(
            graph, source_node, "custom_center", "选定中心点", time_limits, styles
        )
    else:
        if not os.path.exists(objects_path):
            print(f"错误：找不到设施文件 {objects_path}")
            return []

        with open(objects_path, 'r', encoding='utf-8') as f:
            facilities_data = json.load(f)

        features_list = facilities_data['features'] if 'features' in facilities_data else facilities_data

        for feat in features_list:
            props = feat.get('properties', feat)
            obj_id = props.get('objectId') or props.get('id') or 'unknown'
            obj_name = props.get('name') or obj_id

            if target_id and obj_id != target_id:
                continue

            coords = feat.get('geometry', {}).get('coordinates', [0, 0])
            lon, lat = coords[0], coords[1]
            point_m = gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326").to_crs(epsg=3857)[0]
            source_node = min(nodes_list, key=lambda n: Point(n).distance(point_m))
            results.extend(_isochrone_from_node(
                graph, source_node, obj_id, obj_name, time_limits, styles
            ))

    output_filename = os.path.join(data_dir, 'analysis_result_isochrone.json')
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    return results


if __name__ == "__main__":
    run_isochrone_analysis()
