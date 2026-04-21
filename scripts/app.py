import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Citi Bike Coverage Gaps", layout="wide")

st.title("🚲 Lower Manhattan Citi Bike Accessibility")
st.markdown("Identifying underserved blocks based on station proximity.")

@st.cache_data
def load_data():
    gdf = gpd.read_file("data/processed_accessibility.geojson")
    return gdf

@st.cache_data
def load_stations():
    trips = pd.read_csv("data/citibike_tripdata.csv")
    stations = trips[['start_station_name', 'start_lat', 'start_lng']].drop_duplicates()
    return stations

data = load_data()
stations = load_stations()

# Sidebar filters
neighborhood = st.sidebar.multiselect("Filter by Neighborhood", options=sorted(data['ntaname'].dropna().unique()))

# Map Logic
m = folium.Map(location=[40.7128, -74.0060], zoom_start=13, tiles="cartodbpositron")

# Choropleth for all blocks
folium.Choropleth(
    geo_data=data,
    name="Accessibility",
    data=data,
    columns=["GEOID", "dist_to_station"],
    key_on="feature.properties.GEOID",
    fill_color="YlOrRd",
    fill_opacity=0.6,
    line_opacity=0.1,
    legend_name="Distance to Nearest Station (feet)"
).add_to(m)

# Highlight selected neighborhoods as a bold outline
if neighborhood:
    filtered = data[data['ntaname'].isin(neighborhood)]
    folium.GeoJson(
        filtered,
        name="Selected Neighborhoods",
        style_function=lambda _: {
            "fillColor": "#00bfff",
            "color": "#005f8a",
            "weight": 3,
            "fillOpacity": 0.45,
        },
        tooltip=folium.GeoJsonTooltip(fields=["ntaname", "dist_to_station"], aliases=["Neighborhood", "Dist to Station (ft)"])
    ).add_to(m)

# Station dots
station_group = folium.FeatureGroup(name="Citi Bike Stations")
for _, row in stations.iterrows():
    if pd.notna(row['start_lat']) and pd.notna(row['start_lng']):
        folium.CircleMarker(
            location=[row['start_lat'], row['start_lng']],
            radius=4,
            color="#0057a8",
            fill=True,
            fill_color="#4db8ff",
            fill_opacity=0.85,
            weight=1,
            tooltip=row['start_station_name']
        ).add_to(station_group)
station_group.add_to(m)

folium.LayerControl().add_to(m)

st_folium(m, width=1200, height=700)
