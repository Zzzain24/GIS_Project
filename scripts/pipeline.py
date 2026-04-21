import pandas as pd
import geopandas as gpd
from shapely import wkt
from shapely.ops import nearest_points

# 1. LOAD DATA
# Load Census Blocks (CSV with WKT geometry)
blocks_df = pd.read_csv('data/2020_Census_Blocks_20260421.csv')
blocks_df['geometry'] = blocks_df['the_geom'].apply(wkt.loads)
blocks = gpd.GeoDataFrame(blocks_df, crs="EPSG:4326")

# Load NTAs (GeoJSON)
ntas = gpd.read_file('2020_Neighborhood_Tabulation_Areas_(NTAs)_20260421.geojson')

# Load Population (CSV)
pop = pd.read_csv('data/Sheet 2_Full Data_data.csv')

# Load Trip Data to extract station locations
trips = pd.read_csv('data/citibike_tripdata.csv')

# 2. EXTRACT STATION LOCATIONS
# We take the unique start stations to build our station map
stations = trips[['start_station_name', 'start_lat', 'start_lng']].drop_duplicates()
stations_gdf = gpd.GeoDataFrame(
    stations, 
    geometry=gpd.points_from_xy(stations.start_lng, stations.start_lat),
    crs="EPSG:4326"
)

# 3. CLEAN & PREP
# Clean Population NTA names to match the GeoJSON (removing the "(MN)" etc)
pop['ntaname_clean'] = pop['NTA Name'].str.split(' \(').str[0]
ntas['ntaname_clean'] = ntas['ntaname']

# Merge Pop into NTAs
ntas_with_pop = ntas.merge(pop[['ntaname_clean', 'Pop 20']], on='ntaname_clean', how='left')

# 4. SPATIAL ANALYSIS
# Project everything to NY State Plane (Feet) for accurate distance
blocks = blocks.to_crs("EPSG:2263")
stations_gdf = stations_gdf.to_crs("EPSG:2263")
ntas_with_pop = ntas_with_pop.to_crs("EPSG:2263")

# Filter for Manhattan blocks only
blocks = blocks[blocks['BoroName'] == 'Manhattan']

# Spatial Join: Assign NTA name and Population to each block
blocks_final = gpd.sjoin(blocks, ntas_with_pop[['geometry', 'ntaname', 'Pop 20']], how='left', predicate='within')

# Calculate Distance to nearest station
def calculate_min_dist(block_geom, station_points):
    # This finds the distance to the nearest station point
    return block_geom.centroid.distance(station_points.unary_union)

blocks_final['dist_to_station'] = blocks_final.geometry.apply(lambda x: calculate_min_dist(x, stations_gdf))

# 5. EXPORT FOR STREAMLIT
# Convert back to Lat/Lon for web mapping
output = blocks_final[['GEOID', 'ntaname', 'Pop 20', 'dist_to_station', 'geometry']].to_crs("EPSG:4326")
output.to_file("data/processed_accessibility.geojson", driver='GeoJSON')

print("Success! 'processed_accessibility.geojson' is ready for Streamlit.")