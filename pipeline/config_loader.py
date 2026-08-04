import yaml
import os

def load_pipeline_config():
    # Attempt to load pipeline/config.yaml
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def get_dataset_dir():
    config = load_pipeline_config()
    base = os.path.expanduser(config['dataset']['base_dir'])
    return os.path.join(base, config['dataset']['name'])
