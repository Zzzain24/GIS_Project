import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium

# --- CONFIG ---
st.set_page_config(page_title="Citi Bike Coverage Gaps", layout="wide")

st.title("🚲 Lower Manhattan Citi Bike Accessibility")
st.markdown("Identify underserved areas and evaluate accessibility by neighborhood.")

# --- DATA ---
@st.cache_data
def load_data():
    gdf = gpd.read_file("data/processed_accessibility.geojson")
    
    gdf["is_gap"] = gdf["dist_to_station"] > 1000
    gdf["walk_time_min"] = gdf["dist_to_station"] / 264
    
    return gdf

@st.cache_data
def load_stations():
    try:
        trips = pd.read_csv("data/manhattan_citibike_trips.csv")
    except:
        trips = pd.read_csv("data/citibike_tripdata.csv")

    return trips[['start_station_name', 'start_lat', 'start_lng']].drop_duplicates()

data = load_data()
stations = load_stations()

# --- SIDEBAR ---
st.sidebar.header("Analysis Filters")
neighborhoods = sorted(data["ntaname"].dropna().unique())
selected_ntas = st.sidebar.multiselect("Filter by Neighborhood", neighborhoods)

# --- FILTER ---
view_data = data[data["ntaname"].isin(selected_ntas)] if selected_ntas else data

# --- ACCESSIBILITY SCORE ---
def compute_accessibility_score(df):
    df = df.copy()
    max_dist = df["dist_to_station"].max()
    df["norm_dist"] = df["dist_to_station"] / max_dist if max_dist else 0
    df["access_score"] = 100 * (1 - df["norm_dist"])
    return df

view_data = compute_accessibility_score(view_data)

# --- METRICS ---
col1, col2, col3 = st.columns(3)

total_pop = int(view_data["Pop 20"].sum())
gap_pop = int(view_data[view_data["is_gap"]]["Pop 20"].sum())
avg_time = view_data["walk_time_min"].mean()

with col1:
    st.metric("Total Population", f"{total_pop:,}")

with col2:
    pct = (gap_pop / total_pop * 100) if total_pop else 0
    st.metric("Residents in Gaps (>1k ft)", f"{gap_pop:,}", delta=f"{pct:.0f}%")

with col3:
    st.metric("Avg Walk Time", f"{avg_time:.1f} min")

st.divider()

# --- MAP CENTERING LOGIC ---
if selected_ntas and not view_data.empty:
    center = [
        view_data.geometry.centroid.y.mean(),
        view_data.geometry.centroid.x.mean()
    ]
    zoom = 15
else:
    center = [40.7128, -74.0060]
    zoom = 14

# --- MAP ---
m = folium.Map(location=center, zoom_start=zoom, tiles="cartodbpositron")

# Base Choropleth
folium.Choropleth(
    geo_data=data,
    data=data,
    columns=["GEOID", "dist_to_station"],
    key_on="feature.properties.GEOID",
    fill_color="YlOrRd",
    fill_opacity=0.5,
    line_opacity=0.1,
    name="Accessibility",
).add_to(m)

# Highlight selected neighborhoods
if selected_ntas:
    folium.GeoJson(
        view_data,
        name="Selected Neighborhood",
        style_function=lambda x: {
            "fillColor": "transparent",
            "color": "#0D4A25",
            "weight": 4,
            "dashArray": "5,5",
        },
        tooltip=folium.GeoJsonTooltip(fields=["ntaname"], aliases=["Neighborhood:"])
    ).add_to(m)

# Buffers
show_buffers = st.checkbox("Show 5-minute walk radius (1,000ft buffers)", value=False)

if show_buffers:
    buffer_group = folium.FeatureGroup(name="Buffers")
    for _, row in stations.iterrows():
        folium.Circle(
            location=[row["start_lat"], row["start_lng"]],
            radius=304,
            color="#2ecc71",
            fill=True,
            fill_opacity=0.1
        ).add_to(buffer_group)
    buffer_group.add_to(m)

# Stations
station_group = folium.FeatureGroup(name="Stations")

for _, row in stations.iterrows():
    folium.CircleMarker(
        location=[row["start_lat"], row["start_lng"]],
        radius=3,
        color="#0057a8",
        fill=True,
        tooltip=row["start_station_name"]
    ).add_to(station_group)

station_group.add_to(m)

folium.LayerControl().add_to(m)

st_folium(m, width=1000, height=600)

# --- PRIORITY RANKINGS ---
st.subheader("📊 Priority Rankings")
st.caption("Darker red = worse access | Darker blue = higher population share")

priority_df = (
    view_data.groupby("ntaname")
    .agg({
        "access_score": "mean",
        "walk_time_min": "mean",
        "Pop 20": "sum"
    })
    .rename(columns={
        "access_score": "Accessibility Score",
        "walk_time_min": "Avg Walk (min)",
        "Pop 20": "Population"
    })
    .reset_index()
)

total_pop_table = priority_df["Population"].sum()
priority_df["Population %"] = (
    priority_df["Population"] / total_pop_table * 100
    if total_pop_table else 0
)

st.dataframe(
    priority_df.sort_values("Accessibility Score")
    .style
    .background_gradient(subset=["Accessibility Score"], cmap="Reds_r")
    .background_gradient(subset=["Avg Walk (min)"], cmap="Reds")
    .background_gradient(subset=["Population %"], cmap="Blues")
    .format({
        "Accessibility Score": "{:.1f}",
        "Avg Walk (min)": "{:.1f} min",
        "Population": "{:,}",
        "Population %": "{:.1f}%"
    }),
    use_container_width=True
)

# --- METHODOLOGY ---
with st.expander("See Methodology"):
    st.write("""
    - **Data Sources:** NYC Open Data, Citi Bike Trip Data  
    - **Distance Calculation:** EPSG:2263 projection (feet)  
    - **Gap Definition:** > 1000 ft from nearest station  
    - **Accessibility Score:** Normalized inverse distance (0–100)  
    - **Walk Time:** ~3 mph (~264 ft/min)  
    """)