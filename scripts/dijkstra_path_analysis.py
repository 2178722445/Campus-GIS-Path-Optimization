import os
import json
import geopandas as gpd
import networkx as nx
from shapely.geometry import Point, LineString, mapping

from data_config import get_roads_path, get_data_dir


def run_dijkstra_path(start_lon, start_lat, end_lon, end_lat, data_dir=None):
    data_dir = get_data_dir(data_dir)
    roads_path = get_roads_path(data_dir)
    output_path = os.path.join(data_dir, 'analysis_result_dijkstra.json')

    if not os.path.exists(roads_path):
        print(f"错误：找不到路网文件 {roads_path}")
        return []

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
            graph.add_edge(p1, p2, weight=dist)

    if len(graph.nodes) == 0:
        print("错误：路网图为空，无法计算路径")
        return []

    def find_nearest_node(lon, lat):
        point_m = gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326").to_crs(epsg=3857)[0]
        nodes = list(graph.nodes)
        return min(nodes, key=lambda n: Point(n).distance(point_m))

    source_node = find_nearest_node(start_lon, start_lat)
    target_node = find_nearest_node(end_lon, end_lat)

    try:
        path_nodes = nx.shortest_path(graph, source=source_node, target=target_node, weight='weight')
        path_length = nx.shortest_path_length(graph, source=source_node, target=target_node, weight='weight')
    except nx.NetworkXNoPath:
        print("错误：两点间无连通路径")
        return []

    path_line = LineString(path_nodes)
    path_gdf = gpd.GeoSeries([path_line], crs="EPSG:3857").to_crs(epsg=4326)
    walking_time = round(path_length / 72, 1)

    res_item = {
        "objectId": f"path_{start_lon}_{end_lon}",
        "value": round(path_length, 2),
        "level": 2,
        "label": "最短步行路径",
        "style": {"color": "#f97316", "width": 6, "opacity": 0.95},
        "description": f"全长 {round(path_length, 2)} 米，预计步行 {walking_time} 分钟",
        "geometry": mapping(path_gdf.iloc[0]),
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump([res_item], f, ensure_ascii=False, indent=4)

    return [res_item]


if __name__ == "__main__":
    run_dijkstra_path(103.720, 36.110, 103.725, 36.105)