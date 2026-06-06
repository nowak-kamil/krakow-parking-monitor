"""
Parking data preparation – grid normalization and missing slot detection.

This script preprocesses raw parking data by:
  1. Rounding timestamps to the nearest 30-minute interval.
  2. Removing duplicate entries for the same parking and time slot.
  3. Generating a continuous 30-minute timeline for all unique parkings.
  4. Injecting explicit NaNs into the timeline where data points are missing.

The output from this step serves as the foundation for subsequent data imputation.
"""

import pandas as pd

# Configuraction
INPUT= "archiwum_parkingow.csv"
OUTPUT = "Parking_NaaN.csv"


# Loading data
df = pd.read_csv(INPUT, sep=";", encoding="utf-8-sig")
df.columns = ["ts_raw", "parking", "free"]

# Rounding timestamp to full 30 minutes and removing duplicates
df["ts"] = pd.to_datetime(df["ts_raw"]).dt.round("30min")
df = df.sort_values("ts").drop_duplicates(subset=["ts", "parking"])

# Building a complete grid: every 30 minutes for each parking
date_range = pd.date_range(df["ts"].min(), df["ts"].max(), freq="30min")
parkings   = df["parking"].unique()

grid = pd.MultiIndex.from_product(
    [date_range, parkings], names=["ts", "parking"]
)
grid = pd.DataFrame(index=grid).reset_index()

# Append actual data (missing slots will get NaN)
result = grid.merge(df[["ts", "parking", "free"]], on=["ts", "parking"], how="left")

# Name the columns and save
result = result.rename(columns={
    "ts":      "Datetime",
    "parking": "Parking",
    "free":   "Free slots",
})

result.to_csv(OUTPUT, sep=";", index=False, encoding="utf-8-sig")

# Summary
total   = len(result)
nodata   = result["Free slots"].isna().sum()
print(f"Saved: {OUTPUT}")
print(f"  Total rows        : {total}")
print(f"  Rows of data      : {total - nodata}")
print(f"  Missing (null)    : {nodata}")