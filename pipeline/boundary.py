import ee
import os
import json

def get_city_boundary(config: dict) -> ee.FeatureCollection:
    """
    Fetches the boundary for the given region of interest.
    It expects a local GeoJSON file at boundaries/{boundary_name}.geojson
    """
    if 'roi' not in config or 'boundary' not in config['roi']:
        raise ValueError("Config must specify 'roi.boundary'.")
        
    boundary_name = config['roi']['boundary']
    geojson_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'boundaries', f"{boundary_name}.geojson")
    
    if not os.path.exists(geojson_path):
        raise FileNotFoundError(f"Boundary file not found: {geojson_path}")
        
    with open(geojson_path, 'r') as f:
        geo_data = json.load(f)
        
    # We assume standard GeoJSON with a FeatureCollection or a single Polygon
    if geo_data['type'] == 'FeatureCollection':
        # Grab the geometry of the first feature
        geom = geo_data['features'][0]['geometry']
    elif geo_data['type'] == 'Polygon' or geo_data['type'] == 'MultiPolygon':
        geom = geo_data
    else:
        raise ValueError("Unsupported GeoJSON format for boundary.")
        
    ee_geom = ee.Geometry(geom)
    return ee.FeatureCollection([ee.Feature(ee_geom)])
