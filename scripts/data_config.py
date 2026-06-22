import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, 'data')

FACILITIES_FILE = '03_campus_objects.json'
ROADS_FILE = '04_paths_or_roads.geojson'
POLYGONS_FILE = '05_facilities_or_regions.geojson'


def get_data_dir(data_dir=None):
    return data_dir or DATA_DIR


def get_roads_path(data_dir=None):
    return os.path.join(get_data_dir(data_dir), ROADS_FILE)


def get_objects_path(data_dir=None):
    return os.path.join(get_data_dir(data_dir), FACILITIES_FILE)


def get_polygons_path(data_dir=None):
    return os.path.join(get_data_dir(data_dir), POLYGONS_FILE)


def data_ready(data_dir=None):
    roads = get_roads_path(data_dir)
    objects = get_objects_path(data_dir)
    return os.path.exists(roads) and os.path.exists(objects)