import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# Usage check
if len(sys.argv) != 3:
    print("Usage: python pulse_analysis.py <pulses_csv> <waveforms_csv>")
    sys.exit(1)

pulses_file = sys.argv[1]
waveforms_file = sys.argv[2]

# Extract run number
try:
    run_number = pulses_file.split("_")[0].replace("Run", "")
except Exception:
    print("Error: could not extract run number from input file name")
    sys.exit(1)

print(f"Processing Run {run_number}...")
print(f"Loading {pulses_file} and {waveforms_file}...")

# Load CSVs
mqspulses = pd.read_csv(pulses_file)
wfs = pd.read_csv(waveforms_file)


mqspulses.columns = mqspulses.columns.str.strip()
wfs.columns = wfs.columns.str.strip()

print(f"Pulse file contains {len(mqspulses)} entries")
print(f"Waveform file contains {len(wfs)} entries")

# Ensure waveform_index exists in waveform dataframe
if "waveform_index" not in wfs.columns:
    candidates = [c for c in wfs.columns if "waveform" in c.lower()]
    if candidates:
        wfs.rename(columns={candidates[0]: "waveform_index"}, inplace=True)
        print(f"Renamed waveform column '{candidates[0]}' -> 'waveform_index'")
    else:
        print("Error: no 'waveform_index' column found in waveforms CSV")
        sys.exit(1)

# Ensure pulses dataframe has a waveform_index to map from.
# If it's not present, use the pulse DataFrame index, 1:1 with waveforms
if "waveform_index" not in mqspulses.columns:
    mqspulses = mqspulses.reset_index().rename(columns={"index": "waveform_index"})
    print("Added 'waveform_index' to pulses")

# Map channels into wfs
if "chan" in mqspulses.columns:
    try:
        # align dtypes for mapping
        mqspulses["waveform_index"] = mqspulses["waveform_index"].astype(int)
        wfs["waveform_index"] = wfs["waveform_index"].astype(int)
        wfs["chan"] = wfs["waveform_index"].map(mqspulses.set_index("waveform_index")["chan"])
    except Exception as e:
        print(f"Warning: failed to map chan into wfs: {e}")
else:
    print("Warning: 'chan' column not found in pulses file, skipping mapping.")

# Count unique waveforms per channel (handle missing chans)
if "chan" in wfs.columns and wfs["chan"].notna().any():
    unique_counts = wfs.groupby("chan")["waveform_index"].nunique()
    for chan, count in unique_counts.items():
        print(f"  Channel {chan}: {count} unique waveforms")
else:
    print("No channel information available in waveforms (chan missing or all NaN)")

# Save waveforms with channel mapping
out1 = f"wfs_w_chan{run_number}.csv"
wfs.to_csv(out1, index=False)
print(f"Saved waveform+channel mapping to {out1}")

# cutting saturated pulses and those far exceeding SPE range
mqspulses = mqspulses[mqspulses["V"] < 200]
print("Applied V < 200 cut")

x = mqspulses["V"]
y = mqspulses["area"]
chan = mqspulses["chan"]

# Storage for fits and residuals
fit_results = {}

# Iterate over all channels
for ch in mqspulses["chan"].unique():
    chan_data = mqspulses[mqspulses["chan"] == ch]
    if len(chan_data) < 2:
        continue

    slope, intercept = np.polyfit(chan_data["V"], chan_data["area"], 1)
    residuals = chan_data["area"] - (slope * chan_data["V"] + intercept)
    std = np.std(residuals)

    fit_results[ch] = (slope, intercept, std)
    print(f"Channel {ch}: slope={slope:.3f}, intercept={intercept:.3f}, std={std:.3f}")

# Filtering w/in 1 std
filtered_dfs = []
keep_idxs = []

for ch, (slope, intercept, std) in fit_results.items():
    chan_data = mqspulses[mqspulses["chan"] == ch]
    residuals = chan_data["area"] - (slope * chan_data["V"] + intercept)
    mask = np.abs(residuals) <= std
    filtered = chan_data[mask]
    filtered_dfs.append(filtered)
    keep_idxs.extend(filtered.index)

if filtered_dfs:
    filtered_mqspulses = pd.concat(filtered_dfs)
else:
    filtered_mqspulses = mqspulses.iloc[0:0]


# waveform_index in wfs matches pulse DataFrame index (1:1 from C++ reader)
filtered_wfs = wfs[wfs["waveform_index"].isin(keep_idxs)]

# save filtered outputs
out2 = f"filtered_wfs_within_1_std{run_number}.csv"
filtered_wfs.to_csv(out2, index=False)
print(f"Saved filtered waveforms (±1σ) to {out2}")

# set up color map
chan_colors = {
    1: "blue",
    2: "red",
    3: "green",
    4: "gold"
}

chan_dark_colors = {
    1: "navy",
    2: "darkred",
    3: "darkgreen",
    4: "goldenrod"
}
# Plotting
plt.figure(figsize=(8, 6))

legend_elements = []

for ch in sorted(fit_results.keys()):
    chan_data = mqspulses[mqspulses["chan"] == ch]

    # Scatter points
    plt.scatter(
        chan_data["V"],
        chan_data["area"],
        s=6,
        alpha=0.35,
        color=chan_colors.get(ch, "gray"),
        label=f"Channel {ch}"
    )

    slope, intercept, std = fit_results[ch]

    V_fit = np.linspace(chan_data["V"].min(), chan_data["V"].max(), 200)
    fit_line = slope * V_fit + intercept

    # Best-fit line
    plt.plot(
        V_fit,
        fit_line,
        color=chan_dark_colors.get(ch, "black"),
        linewidth=2,
        label=f"Ch {ch} fit"
    )

    # 1σ lines
    plt.plot(
        V_fit,
        fit_line + std,
        linestyle="--",
        color=chan_dark_colors.get(ch, "black"),
        alpha=0.8,
        label=f"Ch {ch} +1σ"
    )
    plt.plot(
        V_fit,
        fit_line - std,
        linestyle="--",
        color=chan_dark_colors.get(ch, "black"),
        alpha=0.8,
        label=f"Ch {ch} −1σ"
    )

plt.title(f"Pulse Height vs Pulse Area (Run {run_number})")
plt.ylim(0, np.percentile(y, 99.5))
plt.xlabel("Pulse Height (mV*10)")
plt.ylabel("Pulse Area (V·ns)")
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend(fontsize=9, ncol=2)
plt.tight_layout()

plt.savefig(f"Plots/pulse_height_vs_area_run{run_number}.png")
plt.close()
print(f"Saved plots to Plots/pulse_height_vs_area_run{run_number}.png")

for ch in sorted(fit_results.keys()):
    chan_data = mqspulses[mqspulses["chan"] == ch]
    slope, intercept, std = fit_results[ch]

    if chan_data.empty:
        continue

    plt.figure(figsize=(8, 6))

    # Scatter
    plt.scatter(
        chan_data["V"],
        chan_data["area"],
        s=6,
        alpha=0.35,
        color=chan_colors.get(ch, "gray"),
        label=f"Channel {ch}"
    )

    # Fit line
    V_fit = np.linspace(chan_data["V"].min(), chan_data["V"].max(), 200)
    fit_line = slope * V_fit + intercept

    plt.plot(
        V_fit,
        fit_line,
        color=chan_dark_colors.get(ch, "black"),
        linewidth=2,
        label="Best fit"
    )

    # 1σ bands
    plt.plot(
        V_fit,
        fit_line + std,
        linestyle="--",
        color=chan_dark_colors.get(ch, "black"),
        alpha=0.8,
        label="+1σ"
    )
    plt.plot(
        V_fit,
        fit_line - std,
        linestyle="--",
        color=chan_dark_colors.get(ch, "black"),
        alpha=0.8,
        label="−1σ"
    )

    plt.title(f"Pulse Height vs Pulse Area (Run {run_number}, Channel {ch})")
    plt.xlabel("Pulse Height (mV*10)")
    plt.ylabel("Pulse Area (V·ns)")
    plt.ylim(0, np.percentile(chan_data["area"], 99.5))
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(fontsize=9)
    plt.tight_layout()

    outname = f"Plots/pulse_height_vs_area_run{run_number}_CH{ch}.png"
    plt.savefig(outname)
    plt.close()

    print(f"Saved per-channel plot to {outname}")