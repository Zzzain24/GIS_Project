# Citi Bike Coverage Gap Analysis — Lower Manhattan

A GIS web application that maps Citi Bike accessibility gaps across Lower Manhattan census blocks. The dashboard identifies underserved neighborhoods by measuring walking distances to the nearest bike station, visualizing equity gaps, and ranking neighborhoods by accessibility score.

## What It Does

- Calculates the distance from every Manhattan census block centroid to the nearest Citi Bike station
- Flags blocks more than 1,000 ft (~5-minute walk) from a station as coverage gaps
- Displays an interactive choropleth map with station markers and optional walk-radius buffers
- Ranks neighborhoods by accessibility score, average walk time, and population share

## Project Structure

```
GIS_Project/
├── data/
│   ├── 2020_Census_Blocks_20260421.csv              # NYC census block geometries
│   ├── 2020_Neighborhood_Tabulation_Areas_*.geojson # NTA boundaries
│   ├── citibike_tripdata.csv                        # Citi Bike trip data (station source)
│   ├── Sheet 2_Full Data_data.csv                   # NTA population data
│   └── processed_accessibility.geojson              # Pipeline output (auto-generated)
├── scripts/
│   ├── pipeline.py   # Spatial processing: joins, distance calc, exports GeoJSON
│   └── app.py        # Streamlit dashboard
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Running Locally

### Prerequisites

- Python 3.10+
- GDAL/GEOS/PROJ system libraries (required by GeoPandas)

On macOS with Homebrew:
```bash
brew install gdal
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run the pipeline (first time or when data changes)

```bash
python scripts/pipeline.py
```

This reads the raw data files and writes `data/processed_accessibility.geojson`.

### Launch the dashboard

```bash
streamlit run scripts/app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Running with Docker

Docker handles all GDAL/GEOS system dependencies automatically — no local GIS library setup needed.

### Option 1: Docker Compose (recommended)

Runs the pipeline first, then starts the Streamlit app:

```bash
docker compose up --build
```

Open [http://localhost:8501](http://localhost:8501).

To stop:
```bash
docker compose down
```

### Option 2: Docker directly

```bash
# Build the image
docker build -t citibike-app .

# Run the pipeline to generate processed data
docker run --rm -v $(pwd)/data:/app/data citibike-app python scripts/pipeline.py

# Run the dashboard
docker run -p 8501:8501 -v $(pwd)/data:/app/data citibike-app
```

> The volume mount (`-v $(pwd)/data:/app/data`) ensures the processed GeoJSON is written back to your local `data/` directory and persists between runs.

---

## Data Sources

| Dataset | Source |
|---|---|
| NYC 2020 Census Blocks | [NYC Open Data](https://opendata.cityofnewyork.us) |
| Neighborhood Tabulation Areas (NTAs) | [NYC Open Data](https://opendata.cityofnewyork.us) |
| Citi Bike Trip Data | [Citi Bike System Data](https://citibikenyc.com/system-data) |
| NTA Population Estimates | NYC DCP |

## Methodology

- **Projection:** EPSG:2263 (NY State Plane, feet) for accurate distance calculations
- **Gap threshold:** > 1,000 ft from nearest station centroid
- **Accessibility score:** Normalized inverse distance, 0–100 (100 = best access)
- **Walk time estimate:** ~264 ft/min (~3 mph walking speed)
- **Population apportionment:** NTA population distributed to blocks by area fraction
