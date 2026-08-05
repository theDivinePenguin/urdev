DATASET_REGISTRY = {
    "dynamic_world": {
        "collection": "GOOGLE/DYNAMICWORLD/V1",
        "band": "label",
        "scale": 10,
        "type": "categorical",
        "reducer": "mode",
        "sparse_before_year": 2017
    },
    "temperature": {
        "collection": "MODIS/061/MOD11A2",
        "band": "LST_Day_1km",
        "scale": 1000,
        "type": "continuous",
        "reducer": "mean",
        "vis_min": 13500,
        "vis_max": 16500,
        "colormap": "inferno"
    },
    "ozone": {
        "collection": "COPERNICUS/S5P/OFFL/L3_O3",
        "band": "O3_column_number_density",
        "scale": 1113.2,
        "type": "continuous",
        "reducer": "mean",
        "vis_min": 0.1,
        "vis_max": 0.2,
        "colormap": "viridis"
    },
    "vegetation": {
        "collection": "MODIS/061/MOD13Q1",
        "band": "NDVI",
        "scale": 250,
        "type": "continuous",
        "reducer": "mean",
        "vis_min": -2000,
        "vis_max": 10000,
        "colormap": "viridis"
    }
}

def get_dataset_profile(name):
    if name not in DATASET_REGISTRY:
        raise ValueError(f"Dataset '{name}' not found. Supported: {list(DATASET_REGISTRY.keys())}")
    return DATASET_REGISTRY[name]
