# Canopy Analysis — Landsat Band Reflectance Collector

A configurable tool for downloading raw Landsat 8/9 surface reflectance data and NLCD land cover by county from Google Earth Engine. Designed for vegetation distress research and reusable by non-profits with minimal technical setup.

---

## How it works

The pipeline has two stages:

1. **Download** (`task download`) — Pulls raw band reflectances, county boundaries, and land cover from Earth Engine. No processing is applied. Data is saved to `data_collected/` for reuse.
2. **Report** (`task report`) — Reads the saved data, computes spectral indices (NDVI, EVI, SAVI, NBR), and generates visualizations. No Earth Engine connection required.

---

## Quickstart

### Prerequisites
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — Python package manager
- [Task](https://taskfile.dev/installation/) — task runner
- A [Google Earth Engine](https://earthengine.google.com/) account with a project ID

### Setup

```bash
# 1. Clone the repo
git clone <repo-url>
cd canopy-analysis

# 2. Copy the env file and add your GEE project ID
cp .env.example .env
# Edit .env: GOOGLEEARTHENGINE_PROJECT_ID=your-project-id

# 3. Install dependencies and authenticate with Earth Engine
task setup
```

### Configure

Edit `config.yml` to set the state(s), counties, date range, and which Landsat bands to collect. This is the only file you need to change.

```yaml
study_area:
  states:
    - fips: "17"
      name: Illinois
      counties:
        - McHenry
        - Cook
        - Lake
```

### Run

```bash
task download   # fetch raw data from Earth Engine (takes several minutes)
task report     # compute indices and generate plots from saved data
```

---

## Docker (no Python required)

```bash
# Build the image
docker build -t canopy-analysis .

# Run — mount your GEE credentials and an output folder
docker run \
  -v ~/.config/earthengine:/root/.config/earthengine:ro \
  -v $(pwd)/data_collected:/app/data_collected \
  canopy-analysis
```

> **Note:** Authenticate with Earth Engine on your host machine first (`task setup`) so the credentials file exists to mount.

---

## Output files

| File | Description |
|------|-------------|
| `data_collected/band_reflectance.csv` | Raw mean surface reflectance per band, per county, per image date |
| `data_collected/county_boundaries.geojson` | TIGER county boundaries — load directly in QGIS, ArcGIS, or Leaflet |
| `data_collected/land_cover.csv` | NLCD land cover class percentages per county |
| `visualizations/spectral_indices.png` | NDVI, EVI, SAVI, NBR time series plots by county |

### Band reference

| Band | Wavelength | Use |
|------|-----------|-----|
| SR_B2 | Blue | EVI blue correction |
| SR_B3 | Green | General reflectance |
| SR_B4 | Red | Vegetation indices |
| SR_B5 | NIR | Vegetation indices |
| SR_B6 | SWIR1 | Moisture, soil |
| SR_B7 | SWIR2 | NBR distress detection |

---

## Spectral indices (computed in `report.py`)

| Index | Formula | Use |
|-------|---------|-----|
| NDVI | (NIR − Red) / (NIR + Red) | General vegetation health |
| EVI | 2.5 × (NIR − Red) / (NIR + 6×Red − 7.5×Blue + 1) | Dense canopy, less soil noise |
| SAVI | (NIR − Red) / (NIR + Red + 0.5) × 1.5 | Sparse vegetation / mixed land |
| NBR | (NIR − SWIR2) / (NIR + SWIR2) | Burn scars, vegetation distress |

---

## Tasks

```
task setup      Install dependencies and authenticate with Earth Engine
task download   Download raw band reflectances, land cover, and boundaries
task report     Compute indices and generate visualizations from saved data
```

---

## License

MIT
