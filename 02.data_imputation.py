"""
Parking data imputation – three strategies depending on the gap size.

  SMALL  (≤ 2 slots, ≤ 1h)   →   forward fill
  MEDIUM (3–8 slots, 1.5–4h) →   linear interpolation
  LARGE  (> 8 slots, > 4h)   →   historical average + linear interpolation

For large gaps:
  The first and last BLEND_SLOTS slots of the gap are a weighted combination of
  linear interpolation (dominating near the boundary) and historical average
  (dominating in the middle). This eliminates unnatural jumps at the gap boundaries.
"""

import pandas as pd
import numpy as np
from pathlib import Path

INPUT  = Path("Parking_NaaN.csv")
OUTPUT = Path("Parking_Imputed.csv")

SMALL_MAX   = 2   # ≤ 2 slots  → forward fill
MEDIUM_MAX  = 8   # ≤ 8 slots → linear interpolation
BLEND_SLOTS = 6   # blending zone for a large gaps (6 × 30min = 3h)

# Loading data

df = pd.read_csv(INPUT, sep=None, engine="python")
df.columns = ["timestamp", "parking", "free_spots"]
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values(["parking", "timestamp"]).reset_index(drop=True)

print(f"Loaded rows:  {len(df)}")
print(f"Parkings:     {df['parking'].nunique()}")
print(f"Missing:      {df['free_spots'].isna().sum()}\n")

# Lookup of historical average

df["is_weekend"] = df["timestamp"].dt.dayofweek.isin([5, 6]).astype(int)
df["time_slot"]  = df["timestamp"].dt.hour * 2 + df["timestamp"].dt.minute // 30

hist_mean = (
    df[df["free_spots"].notna()]
    .groupby(["parking", "is_weekend", "time_slot"])["free_spots"]
    .mean()
)

# Blending weight function

def linear_weight(k: int, gap_size: int, blend_slots: int) -> float:
    """
    Weight for linear interpolation in the k-th slot of the gap (k=0 is the first slot).
    1.0 = pure linear interpolation, 0.0 = pure historical average.
    Drops linearly from 1 to 0 over blend_slots slots from each boundary.
    """

    dist = min(k + 1, gap_size - k)  # distance from the closer border
    return float(max(0.0, 1.0 - (dist - 1) / blend_slots))

# Imputation for each parking

result_frames = []

for park in sorted(df["parking"].unique()):
    sub = df[df["parking"] == park].set_index("timestamp").sort_index()

    full_idx = pd.date_range(sub.index.min(), sub.index.max(), freq="30min")
    sub = sub.reindex(full_idx)
    sub["parking"]    = park
    sub["is_weekend"] = sub.index.dayofweek.isin([5, 6]).astype(int)
    sub["time_slot"]  = sub.index.hour * 2 + sub.index.minute // 30

    series    = sub["free_spots"].copy().astype(float)
    fill_type = pd.Series("", index=sub.index, dtype=str)

    idx_list = list(sub.index)
    i = 0

    while i < len(idx_list):
        ts = idx_list[i]

        if pd.isna(series[ts]):
            gap_start = i
            while i < len(idx_list) and pd.isna(series[idx_list[i]]):
                i += 1
            gap_end  = i
            gap_size = gap_end - gap_start

            v_before = series[idx_list[gap_start - 1]] if gap_start > 0 else np.nan
            v_after  = series[idx_list[gap_end]]       if gap_end < len(idx_list) else np.nan

            for k, j in enumerate(range(gap_start, gap_end)):
                slot_ts = idx_list[j]

                # Small gap
                if gap_size <= SMALL_MAX:
                    series[slot_ts]    = v_before
                    fill_type[slot_ts] = "forward_fill"

                # Medium gap
                elif gap_size <= MEDIUM_MAX:
                    if pd.notna(v_before) and pd.notna(v_after):
                        frac = (k + 1) / (gap_size + 1)
                        series[slot_ts] = v_before + frac * (v_after - v_before)
                    elif pd.notna(v_before):
                        series[slot_ts] = v_before
                    else:
                        series[slot_ts] = v_after
                    fill_type[slot_ts] = "linear interpolation"

                # Large gap
                else:
                    # Historical part
                    key  = (park, int(sub.loc[slot_ts, "is_weekend"]),
                            int(sub.loc[slot_ts, "time_slot"]))
                    hist = hist_mean.get(key, np.nan)

                    # Linear part
                    if pd.notna(v_before) and pd.notna(v_after):
                        frac   = (k + 1) / (gap_size + 1)
                        linear = v_before + frac * (v_after - v_before)
                        w      = linear_weight(k, gap_size, BLEND_SLOTS)
                    else:
                        # Missing one boundary – historical average only
                        linear, w = hist, 0.0

                    if pd.notna(hist):
                        series[slot_ts] = w * linear + (1 - w) * hist
                    elif pd.notna(linear):
                        series[slot_ts] = linear

                    fill_type[slot_ts] = "Hist. avg + linear interpol."

        else:
            i += 1

    sub["free_spots_imputed"] = series.round(0).astype("Int64")
    sub["fill_type"]          = fill_type

    result_frames.append(
        sub[["parking", "free_spots", "free_spots_imputed", "fill_type"]]
    )

# Merge and export

result = pd.concat(result_frames).reset_index().rename(columns={"index": "timestamp"})
result = result.sort_values(["parking", "timestamp"])

result = result.rename(columns={
    "timestamp":          "Datetime",
    "parking":            "Parking",
    "free_spots":         "Free Slots Original",
    "free_spots_imputed": "Free Slots Imputation",
    "fill_type":          "Imputation type",
})

result.to_csv(OUTPUT, index=False, encoding="utf-8-sig")

# Summary

filled = result[result["Imputation type"] != ""]
print("Used Strategies:")
print(filled["Imputation type"].value_counts().to_string())
print(f"\nTotal imputed:   {len(filled):,} slots")
print(f"Remaining NaNs:  {result['Free Slots Imputation'].isna().sum()}")
print(f"\nSaved to: {OUTPUT}")