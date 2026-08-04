import os
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import yaml

def generate_charts(dataset_dir: str):
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    city_name = config.get('regions', {}).get('osmnx_place_query', 'Urban Area')
    start_year = config.get('start_year', 2016)
    end_year = config.get('end_year', 2026)
    analysis_dir = os.path.join(dataset_dir, "analysis")
    vis_dir = os.path.join(dataset_dir, "visualization")
    
    # 1. Urban Expansion Bar Chart
    yearly_csv = os.path.join(analysis_dir, "yearly_landcover.csv")
    if os.path.exists(yearly_csv):
        df = pd.read_csv(yearly_csv)
        plt.figure(figsize=(10, 6))
        plt.bar(df['year'], df['built'], color='gray', zorder=2)
        plt.grid(axis='y', linestyle='--', alpha=0.7, zorder=1)
        plt.title(f'{city_name} Urban Expansion ({start_year}-{end_year})')
        plt.xlabel('Year')
        plt.ylabel('Built Area (km²)')
        plt.ylim(700, 900)
        
        plt.tight_layout()
        chart_path = os.path.join(vis_dir, "urban_expansion_chart.png")
        plt.savefig(chart_path, dpi=300)
        plt.close()
        print(f"Saved Urban Expansion chart to {chart_path}")
        
    # 2. Land Conversion Sankey Diagram
    transition_csv = os.path.join(analysis_dir, "transition_matrix_2016_2026.csv")
    if os.path.exists(transition_csv):
        tdf = pd.read_csv(transition_csv)
        
        # We want to focus on what transitioned TO built
        # and maybe some other major transitions.
        # The user specifically mentioned Crops->Built, Scrub->Built, etc.
        
        # Filter for transitions where area > 5 km2 (to keep chart clean)
        # and ignore self-transitions (e.g. Built->Built)
        tdf = tdf[(tdf['from_class'] != tdf['to_class']) & (tdf['area_km2'] > 5)]
        
        nodes = list(pd.concat([tdf['from_class'], tdf['to_class']]).unique())
        
        # Sankey diagram requires source and target indices
        node_dict = {node: i for i, node in enumerate(nodes)}
        
        sources = [node_dict[src] for src in tdf['from_class']]
        targets = [node_dict[tgt] for tgt in tdf['to_class']]
        values = tdf['area_km2'].tolist()
        
        fig = go.Figure(data=[go.Sankey(
            node = dict(
              pad = 15,
              thickness = 20,
              line = dict(color = "black", width = 0.5),
              label = nodes,
            ),
            link = dict(
              source = sources,
              target = targets,
              value = values
          ))])
        
        fig.update_layout(title_text="Land Cover Conversions (2016-2026) > 5 km²", font_size=10)
        sankey_path = os.path.join(vis_dir, "land_conversion_sankey.html")
        fig.write_html(sankey_path)
        print(f"Saved Sankey diagram to {sankey_path}")

if __name__ == '__main__':
    base_dir = os.path.join(os.path.expanduser('~'), 'Documents', 'urdev', 'urban_dataset_v7')
    generate_charts(base_dir)
