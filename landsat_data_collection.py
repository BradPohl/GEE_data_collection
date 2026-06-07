import json
import os
import yaml
import ee
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()


def load_config(path="config.yml"):
    with open(path) as f:
        return yaml.safe_load(f)


def build_counties(cfg):
    tiger_year = cfg["study_area"]["tiger_year"]
    counties_fc = ee.FeatureCollection(f"TIGER/{tiger_year}/Counties")

    state_filters = []
    for state in cfg["study_area"]["states"]:
        state_filters.append(
            ee.Filter.And(
                ee.Filter.eq("STATEFP", state["fips"]),
                ee.Filter.inList("NAME", state["counties"])
            )
        )

    return counties_fc.filter(
        ee.Filter.Or(*state_filters) if len(state_filters) > 1 else state_filters[0]
    )


def mask_clouds(image):
    qa = image.select("QA_PIXEL")
    cloud_bit = 1 << 3
    cloud_shadow_bit = 1 << 4
    mask = (
        qa.bitwiseAnd(cloud_bit).eq(0)
        .And(qa.bitwiseAnd(cloud_shadow_bit).eq(0))
    )
    return image.updateMask(mask).copyProperties(image, ["system:time_start"])


def build_collection(cfg):
    date_cfg = cfg["collection"]["date_range"]

    base = None
    for col_id in cfg["collection"]["landsat_collections"]:
        col = ee.ImageCollection(col_id)
        base = col if base is None else base.merge(col)

    return (
        base
        .filterDate(date_cfg["start"], date_cfg["end"])
        .filter(ee.Filter.lt("CLOUD_COVER", cfg["collection"]["max_cloud_cover"]))
        .map(mask_clouds)
    )


def export_boundaries(counties, cfg):
    boundaries_file = cfg["output"].get("boundaries_file")
    if not boundaries_file:
        return
    os.makedirs(os.path.dirname(boundaries_file), exist_ok=True)
    geojson = counties.getInfo()
    with open(boundaries_file, "w") as f:
        json.dump(geojson, f)
    print(f"Boundaries saved to {boundaries_file}")


def extract_band_reflectance(collection, counties, cfg):
    bands = cfg["collection"]["bands"]
    scale = cfg["processing"]["scale"]
    date_cfg = cfg["collection"]["date_range"]
    start_year = int(date_cfg["start"][:4])
    end_year = int(date_cfg["end"][:4])
    bands_file = cfg["output"]["bands_file"]
    fips_to_state = {s["fips"]: s["name"] for s in cfg["study_area"]["states"]}

    os.makedirs(os.path.dirname(bands_file), exist_ok=True)

    aoi = counties.geometry()

    def extract_county_bands(image):
        date = image.date().format("YYYY-MM-dd")
        return (
            image.select(bands)
            .reduceRegions(
                collection=counties,
                reducer=ee.Reducer.mean(),
                scale=scale,
                tileScale=4,
            )
            .map(lambda f: f.set("date", date))
        )

    write_header = not os.path.exists(bands_file)
    for year in tqdm(range(start_year, end_year + 1), desc="Fetching bands", unit="yr"):
        year_collection = collection.filterBounds(aoi).filterDate(f"{year}-01-01", f"{year+1}-01-01")
        time_series = year_collection.map(extract_county_bands).flatten()
        records = time_series.getInfo()["features"]

        rows = []
        for f in records:
            props = f["properties"]
            if any(props.get(b) is None for b in bands):
                continue
            row = {
                "date": props["date"],
                "county": props["NAME"],
                "state": fips_to_state.get(props["STATEFP"], props["STATEFP"]),
            }
            for b in bands:
                row[b] = props[b]
            rows.append(row)

        if rows:
            df_year = pd.DataFrame(rows)
            df_year.to_csv(bands_file, mode="a", index=False, header=write_header)
            write_header = False

    print(f"Band reflectance saved to {bands_file}")


def extract_land_cover(counties, cfg):
    lc_cfg = cfg.get("land_cover", {})
    if not lc_cfg.get("enabled"):
        return

    output_file = lc_cfg["output_file"]
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    fips_to_state = {s["fips"]: s["name"] for s in cfg["study_area"]["states"]}

    nlcd = (
        ee.ImageCollection(lc_cfg["dataset"])
        .filter(ee.Filter.eq("system:index", str(lc_cfg["year"])))
        .first()
    )

    hist = nlcd.select("landcover").reduceRegions(
        collection=counties,
        reducer=ee.Reducer.frequencyHistogram(),
        scale=30,
    )

    records = hist.getInfo()["features"]
    rows = []
    for f in records:
        props = f["properties"]
        class_counts = props.get("histogram", {})
        total = sum(class_counts.values()) or 1
        row = {
            "county": props["NAME"],
            "state": fips_to_state.get(props["STATEFP"], props["STATEFP"]),
        }
        for cls, count in class_counts.items():
            row[f"class_{cls}_pct"] = round(count / total * 100, 4)
        rows.append(row)

    pd.DataFrame(rows).to_csv(output_file, index=False)
    print(f"Land cover saved to {output_file}")


def main():
    cfg = load_config()
    # ee.Authenticate()  # Run once to cache credentials
    ee.Initialize(project=os.getenv("GOOGLEEARTHENGINE_PROJECT_ID"))

    counties = build_counties(cfg)
    export_boundaries(counties, cfg)

    collection = build_collection(cfg)
    extract_band_reflectance(collection, counties, cfg)
    extract_land_cover(counties, cfg)


if __name__ == "__main__":
    main()
