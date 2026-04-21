import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Citi Bike Coverage Gaps", layout="wide")

st.title("🚲 Lower Manhattan Citi Bike Accessibility")
st.markdown("Identifying underserved blocks based on station proximity and population density.")

@st.cache_data
def load_data():
    gdf = gpd.read_file("data/processed_accessibility.geojson")
    # Define a Gap as > 1000 ft (approx 5 min walk)
    gdf['is_gap'] = gdf['dist_to_station'] > 1000
    return gdf

@st.cache_data
def load_stations():
    # Use the cleaned manhattan data if available
    try:
        trips = pd.read_csv("data/manhattan_citibike_trips.csv")
    except:
        trips = pd.read_csv("data/citibike_tripdata.csv")
        
    stations = trips[['start_station_name', 'start_lat', 'start_lng']].drop_duplicates()
    return stations

data = load_data()
stations = load_stations()

# --- SIDEBAR & METRICS ---
st.sidebar.header("Analysis Filters")
neighborhoods = sorted(data['ntaname'].dropna().unique())
selected_ntas = st.sidebar.multiselect("Filter by Neighborhood", options=neighborhoods)

# Filter logic
view_data = data[data['ntaname'].isin(selected_ntas)] if selected_ntas else data

# --- TOP LEVEL METRICS ---
col1, col2, col3 = st.columns(3)
with col1:
    total_pop = int(view_data['Pop 20'].sum())
    st.metric("Total Population", f"{total_pop:,}")
with col2:
    gap_pop = int(view_data[view_data['is_gap'] == True]['Pop 20'].sum())
    st.metric("Residents in Gaps (>1k ft)", f"{gap_pop:,}", delta=f"{int((gap_pop/total_pop)*100)}% of Total", delta_color="inverse")
with col3:
    avg_dist = int(view_data['dist_to_station'].mean())
    st.metric("Avg. Walk to Station", f"{avg_dist} ft")

st.divider()

# --- MAP SECTION ---
col_map, col_stats = st.columns([3, 1])

with col_map:
    # Use a Dark style to make the heatmap pop
    m = folium.Map(location=[40.7128, -74.0060], zoom_start=14, tiles="cartodbpositron")

    # Access Category logic for specific styling
    folium.Choropleth(
        geo_data=data,
        name="Accessibility Heatmap",
        data=data,
        columns=["GEOID", "dist_to_station"],
        key_on="feature.properties.GEOID",
        fill_color="YlOrRd",
        fill_opacity=0.6,
        line_opacity=0.1,
        legend_name="Distance to Station (ft)"
    ).add_to(m)

    # Walkability Buffers (5-minute walk radius)
    show_buffers = st.checkbox("Show 5-minute walk radius (1,000ft buffers)", value=False)
    if show_buffers:
        buffer_group = folium.FeatureGroup(name="Walkability Buffers")
        for _, row in stations.iterrows():
            # 1000 ft is roughly 304 meters
            folium.Circle(
                location=[row['start_lat'], row['start_lng']],
                radius=304, 
                color="#2ecc71",
                fill=True,
                fill_opacity=0.1,
                weight=1
            ).add_to(buffer_group)
        buffer_group.add_to(m)

    # Station dots
    station_group = folium.FeatureGroup(name="Citi Bike Stations")
    for _, row in stations.iterrows():
        folium.CircleMarker(
            location=[row['start_lat'], row['start_lng']],
            radius=3,
            color="#0057a8",
            fill=True,
            tooltip=row['start_station_name']
        ).add_to(station_group)
    station_group.add_to(m)

    folium.LayerControl().add_to(m)
    st_folium(m, width=900, height=600)

with col_stats:
    st.subheader("Priority Rankings")
    st.write("Neighborhoods with furthest average distances:")
    
    # Calculate neighborhood-level stats
    priority_df = data.groupby('ntaname').agg({
        'dist_to_station': 'mean',
        'Pop 20': 'sum'
    }).rename(columns={'dist_to_station': 'Avg Dist (ft)', 'Pop 20': 'Population'})
    
    st.dataframe(
        priority_df.sort_values('Avg Dist (ft)', ascending=False).style.background_gradient(subset=['Avg Dist (ft)'], cmap='Reds'),
        use_container_width=True
    )

# --- EXPANDABLE METHODOLOGY ---
with st.expander("See Methodology"):
    st.write("""
        - **Data Sources:** NYC Open Data (2020 Census Blocks, NTAs), Citi Bike Trip History.
        - **Projection:** Distance calculated using **EPSG:2263** (New York Long Island State Plane) for accuracy in feet.
        - **Definition of a Gap:** Any census block centroid located further than 1,000 feet from an active station.
    """)