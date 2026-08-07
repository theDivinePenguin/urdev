import os
import json
import glob
import subprocess

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dataset_dirs = sorted(glob.glob(os.path.join(base_dir, "data", "urban_dataset_*")))
    
    for dataset_dir in dataset_dirs:
        if not os.path.isdir(dataset_dir):
            continue
            
        json_path = os.path.join(dataset_dir, "dataset.json")
        if not os.path.exists(json_path):
            print(f"Skipping {os.path.basename(dataset_dir)}: no dataset.json found")
            continue
            
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
                
            config = data.get("config", {})
            
            # Extract parameters
            years = data.get("years", [])
            
            start_year = config.get("start_year")
            if start_year is None and years:
                start_year = min(years)
                
            end_year = config.get("end_year")
            if end_year is None and years:
                end_year = max(years)
                
            dataset_name = config.get("dataset", config.get("source", "dynamic_world"))
            
            if start_year is None or end_year is None:
                print(f"Skipping {os.path.basename(dataset_dir)}: could not determine start or end year")
                continue
                
            print(f"\n{'='*50}\nProcessing {os.path.basename(dataset_dir)}\n{'='*50}")
            
            # Ensure analysis folder exists
            analysis_dir = os.path.join(dataset_dir, "analysis")
            os.makedirs(analysis_dir, exist_ok=True)
            
            script_path = os.path.join(base_dir, "pipeline", "generate_analysis.py")
            cmd = [
                "python3", script_path,
                "--dataset-dir", dataset_dir,
                "--start-year", str(start_year),
                "--end-year", str(end_year),
                "--dataset", dataset_name
            ]
            
            subprocess.run(cmd, check=True)
            print(f"Analysis files saved to {analysis_dir}")
            
        except Exception as e:
            print(f"Error processing {dataset_dir}: {e}")

if __name__ == "__main__":
    main()
