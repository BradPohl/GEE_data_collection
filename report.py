import os
import yaml
import pandas as pd
import matplotlib.pyplot as plt


def load_config(path="config.yml"):
    with open(path) as f:
        return yaml.safe_load(f)


def compute_indices(df):
    nir, red, blue, swir2 = df["SR_B5"], df["SR_B4"], df["SR_B2"], df["SR_B7"]
    df["ndvi"] = (nir - red) / (nir + red)
    df["evi"]  = 2.5 * (nir - red) / (nir + 6 * red - 7.5 * blue + 1)
    df["savi"] = (nir - red) / (nir + red + 0.5) * 1.5
    df["nbr"]  = (nir - swir2) / (nir + swir2)
    return df


def plot_indices(df, cfg):
    out = cfg["output"]
    date_cfg = cfg["collection"]["date_range"]
    state_names = ", ".join(s["name"] for s in cfg["study_area"]["states"])
    year_range = f"{date_cfg['start'][:4]}–{date_cfg['end'][:4]}"

    indices = ["ndvi", "evi", "savi", "nbr"]
    labels  = ["NDVI", "EVI", "SAVI", "NBR"]

    fig, axes = plt.subplots(len(indices), 1, figsize=(14, 4 * len(indices)), sharex=True)
    fig.suptitle(f"{state_names} — Spectral Indices by County (Landsat 8/9, {year_range})", fontsize=13)

    counties = df["county"].unique()
    for ax, idx, label in zip(axes, indices, labels):
        for county in counties:
            group = df[df["county"] == county].sort_values("date")
            ax.plot(group["date"], group[idx], marker="o", markersize=2, linewidth=1, label=county)
        ax.set_ylabel(label)
        ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel("Date")
    axes[0].legend(loc="upper left", fontsize=7, ncol=2)

    plt.tight_layout()
    os.makedirs(os.path.dirname(out["plot_file"]), exist_ok=True)
    plt.savefig(out["plot_file"], dpi=out["plot_dpi"])
    plt.show()
    print(f"Plot saved to {out['plot_file']}")


def main():
    cfg = load_config()
    bands_file = cfg["output"]["bands_file"]

    if not os.path.exists(bands_file):
        raise FileNotFoundError(
            f"{bands_file} not found — run 'task download' first."
        )

    df = pd.read_csv(bands_file, parse_dates=["date"])
    df = compute_indices(df)
    plot_indices(df, cfg)


if __name__ == "__main__":
    main()
