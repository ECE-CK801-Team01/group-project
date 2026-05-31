import json
import os
import sys
from datetime import datetime
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
 
sns.set_theme(style="whitegrid")
 
CHARTS_DIR = "charts"
os.makedirs(CHARTS_DIR, exist_ok=True)
 
BIN_NAMES = {
    "pir-01": "Cafeteria",
    "pir-02": "Hallway",
    "pir-03": "Lab Room",
}
 
BIN_PALETTE = {
    "Cafeteria": "#e07a5f",   
    "Hallway":   "#3d5a80",   
    "Lab Room":  "#81b29a",   
}
 
BIN_ORDER = ["Cafeteria", "Hallway", "Lab Room"]
 

def load_events(filepath):
    """Read a JSONL event log and return a tidy DataFrame."""
    records = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
 
    df = pd.DataFrame(records)
 
    if df.empty:
        return df
 
    # Rename device-id (hyphen breaks df.device_id attr access) for ergonomics
    if "device-id" in df.columns:
        df = df.rename(columns={"device-id": "device_id"})
 
    if "resultTime" in df.columns:
        df["timestamp"] = pd.to_datetime(df["resultTime"], utc=True)
    elif "event_time" in df.columns:
        df["timestamp"] = pd.to_datetime(df["event_time"], utc=True)
 
    if "timestamp" in df.columns:
        df["hour"] = df["timestamp"].dt.hour
        df["day_of_week"] = df["timestamp"].dt.day_name()
        df["date"] = df["timestamp"].dt.date
        df["minute"] = df["timestamp"].dt.minute
 
    if "device_id" in df.columns:
        df["bin"] = df["device_id"].map(BIN_NAMES).fillna(df["device_id"])
 
    return df
 
 

# Chart 1 — Events per hour, stacked by bin

def plot_events_per_hour(df):
    hourly = (
        df.groupby(["hour", "bin"]).size().reset_index(name="event_count")
    )
    pivot = hourly.pivot(index="hour", columns="bin", values="event_count").fillna(0)
    pivot = pivot.reindex(columns=[c for c in BIN_ORDER if c in pivot.columns])
 
    fig, ax = plt.subplots(figsize=(10, 5))
    pivot.plot(kind="bar", stacked=True, color=[BIN_PALETTE[c] for c in pivot.columns], ax=ax, width=0.85)
    ax.set_xlabel("Hour of Day")
    ax.set_ylabel("Number of Events")
    ax.set_title("Motion Events by Hour of Day (stacked by bin)")
    ax.legend(title="Bin")
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "events_per_hour.png"), dpi=150)
    plt.close(fig)
    print("Saved events_per_hour.png")
 
 

# Chart 2 — Latency distribution, KDE overlaid per bin

def plot_latency_distribution(df):
    if "pipeline_latency_ms" not in df.columns:
        print("Skipping latency_distribution.png — no pipeline_latency_ms.")
        return
 
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.histplot(
        data=df,
        x="pipeline_latency_ms",
        hue="bin",
        hue_order=BIN_ORDER,
        palette=BIN_PALETTE,
        kde=True,
        alpha=0.4,
        ax=ax,
    )
    ax.set_xlabel("Pipeline Latency (ms)")
    ax.set_ylabel("Frequency")
    ax.set_title("Distribution of Pipeline Latency (per bin)")
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "latency_distribution.png"), dpi=150)
    plt.close(fig)
    print("Saved latency_distribution.png")
 
 
# Chart 3 — Events over time, line per bin

def plot_events_over_time(df):
    daily = (
        df.groupby(["date", "bin"]).size().reset_index(name="event_count")
    )
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.lineplot(
        data=daily,
        x="date",
        y="event_count",
        hue="bin",
        hue_order=BIN_ORDER,
        palette=BIN_PALETTE,
        marker="o",
        ax=ax,
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Number of Events")
    ax.set_title("Daily Motion Events Over Time (per bin)")
    plt.xticks(rotation=45)
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "events_over_time.png"), dpi=150)
    plt.close(fig)
    print("Saved events_over_time.png")
 
 
# Chart 4 — Heatmap, three panels (one per bin), hour vs day-of-week

def plot_heatmap(df):
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    all_hours = list(range(24))
    bins_present = [b for b in BIN_ORDER if b in df["bin"].unique()]
    n = len(bins_present)

    fig, axes = plt.subplots(n, 1, figsize=(11, 3.5 * n), sharex=True)
    if n == 1:
        axes = [axes]
 
    # Build pivots forcing the full 24-hour range so all panels align.
    pivots = {}
    for bin_name in bins_present:
        sub = df[df["bin"] == bin_name]
        counts = (
            sub.groupby(["day_of_week", "hour"]).size().reset_index(name="count")
        )
        pivot = counts.pivot(index="day_of_week", columns="hour", values="count")
        pivot = pivot.reindex(index=day_order, columns=all_hours).fillna(0)
        pivots[bin_name] = pivot
    vmax = max((p.values.max() for p in pivots.values()), default=1)
 
    for ax, bin_name in zip(axes, bins_present):
        sns.heatmap(pivots[bin_name], cmap="YlOrRd", annot=False, linewidths=0.5, vmin=0, vmax=vmax, cbar=True,ax=ax)
        ax.set_xlabel("Hour of Day" if ax is axes[-1] else "")
        ax.set_ylabel("")
        ax.set_title(bin_name)
 
    fig.suptitle("Motion Events: Hour × Day of Week (per bin)", y=1.0)
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "heatmap_hour_day.png"),
                dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("Saved heatmap_hour_day.png")
 
 

# Chart 5 — Latency over time, scatter colored by bin

def plot_latency_over_time(df):
    if "pipeline_latency_ms" not in df.columns or "timestamp" not in df.columns:
        print("Skipping latency_over_time.png — required columns missing.")
        return
    fig,ax = plt.subplots(figsize=(10, 5))
    sns.scatterplot(data=df, x="timestamp", y="pipeline_latency_ms", hue="bin", hue_order=BIN_ORDER, palette=BIN_PALETTE,alpha=0.5,s=15, ax=ax)
    ax.set_xlabel("Time")
    ax.set_ylabel("Pipeline Latency (ms)")
    ax.set_title("Pipeline Latency Over Time (per bin)")
    plt.xticks(rotation=45)
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "latency_over_time.png"), dpi=150)
    plt.close(fig)
    print("Saved latency_over_time.png")
 
 

# Chart 6 (extra) — Latency boxplot per bin
# Answers: "which machine is consistently slower? what's the spread?"
# Chosen because it shows median + IQR + outliers more clearly than KDE

def plot_latency_boxplot(df):
    if "pipeline_latency_ms" not in df.columns:
        print("Skipping latency_boxplot_per_bin.png — no pipeline_latency_ms.")
        return
 
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.boxplot(data=df, x="bin", y="pipeline_latency_ms", hue="bin", order=BIN_ORDER, palette=BIN_PALETTE, legend=False, ax=ax)
    ax.set_xlabel("Bin")
    ax.set_ylabel("Pipeline Latency (ms)")
    ax.set_title("Pipeline Latency Distribution per Bin")
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "latency_boxplot_per_bin.png"), dpi=150)
    plt.close(fig)
    print("Saved latency_boxplot_per_bin.png")
 
 
# Chart 7 (extra) — Cumulative events over time, line per bin
# Answers: "growth rate per bin — which one outpaces others?"
# Chosen because line slope encodes rate visibly.

def plot_cumulative_events(df):
    df_sorted = df.sort_values("timestamp").copy()
    df_sorted["cum_count"] = df_sorted.groupby("bin").cumcount() + 1
 
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.lineplot(data=df_sorted, x="timestamp", y="cum_count", hue="bin", hue_order=BIN_ORDER, palette=BIN_PALETTE, ax=ax)
    ax.set_xlabel("Time")
    ax.set_ylabel("Cumulative Event Count")
    ax.set_title("Cumulative Motion Events Over Time (per bin)")
    plt.xticks(rotation=45)
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "cumulative_events.png"), dpi=150)
    plt.close(fig)
    print("Saved cumulative_events.png")
 
 
if __name__ == "__main__":
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        filepath = "data/demo_events.jsonl"
 
    print(f"Loading events from: {filepath}")
    df = load_events(filepath)
    print(f"Loaded {len(df)} events.")
 
    if df.empty:
        print("No data. Run generate_demo_data.py first (or feed real JSONL).")
        sys.exit(1)
 
    plot_events_per_hour(df)
    plot_latency_distribution(df)
    plot_events_over_time(df)
    plot_heatmap(df)
    plot_latency_over_time(df)
    plot_latency_boxplot(df)
    plot_cumulative_events(df)
 
    print(f"All charts saved to {CHARTS_DIR}/")