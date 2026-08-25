#!/usr/bin/env python3

import argparse
import os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import imageio


def rm_column_spaces(df):
    df = df.copy()
    df.columns = df.columns.str.strip()
    return df


def find_waveform_index_col(cols):
    for c in cols:
        if "waveform" in c.lower():
            return c
    return None

def extract_run_number(filename):
    # Filename format is always wfs_w_chan{RNUM}.csv or filtered_wfs_within_1_std{RNUM}.csv
    bn = Path(filename).stem  # strip .csv
    return bn.split("chan")[-1] if "chan" in bn else bn.replace("filtered_wfs_within_1_std", "")

def bin_waveforms_by_peak(
    df,
    vmin,
    vmax,
    waveform_index_col="waveform_index",
    max_waveforms=3000
):
    binned = []
    seen = 0

    # Select waveform IDs in this bin using precomputed peaks
    wf_ids = df.loc[
        (df["peak_mV"] >= vmin) & (df["peak_mV"] <= vmax),
        waveform_index_col
    ].unique()

    for wf_id in wf_ids:
        if seen >= max_waveforms:
            break

        g = df[df[waveform_index_col] == wf_id]

        t = g["time (ns)"].to_numpy()
        v = g["voltage (mV)"].to_numpy()

        t = t - t.min()
        peak = v.max()
        if peak == 0:
            continue

        v = v / peak
        binned.append((t, v))
        seen += 1

    return binned

# revisit naming+function
def save_normalized_average_csv(t_common, mean, std, out_path):
    df_out = pd.DataFrame({
        "time (ns)": t_common,
        "normalized average": mean,
        "+1 STD": mean + std,
        "-1 STD": mean - std
    })
    df_out.to_csv(out_path, index=False)

def interpolate_and_average(
    groups,
    num_points=1000,
    x_end=250,
    max_waveforms=None
):
    """
    Interpolate waveforms to a common time axis and compute mean/std online
    without stacking full matrices.
    """

    if not groups:
        return None, None, None

    t_common = np.linspace(0, x_end, num_points)
    sum_v = np.zeros(num_points, dtype=np.float64)
    sum_v2 = np.zeros(num_points, dtype=np.float64)
    count = 0

    for i, (t, v) in enumerate(groups):
        if max_waveforms is not None and i >= max_waveforms:
            break

        interp_v = np.interp(t_common, t, v)
        sum_v += interp_v
        sum_v2 += interp_v ** 2
        count += 1

    if count == 0:
        return None, None, None

    mean = sum_v / count
    std = np.sqrt(sum_v2 / count - mean ** 2)

    return t_common, mean, std


def compute_overall_normalized_from_filtered(filtered_wfs_chan_df,
                                             num_points=1000,
                                             x_end=250):
    groups = []
    for _, g in filtered_wfs_chan_df.groupby("waveform_index"):
        t = g["time (ns)"].values
        v = g["voltage (mV)"].values
        t = t - t.min()
        peak = v.max()
        if peak != 0:
            v = v / peak
        else:
            v = np.zeros_like(v)  # or skip it: continue
        groups.append((t, v))   
        
    if not groups:
        return None, None, None

    return interpolate_and_average(
        groups,
        num_points=num_points,
        x_end=x_end
    )


def create_comparison_gif_per_channel(
    clean_df,
    overall_t,
    overall_mean,
    overall_plus,
    overall_minus,
    save_gif_path,
    start,
    stop,
    step,
    bin_width,
    num_points=1000,
    x_end=250,
    ylim_factor=1.2,
    waveform_index_col="waveform_index"
):
    """
    Makes a GIF comparing the overall normalized average waveform to bin-averaged waveforms across voltage bins.
    Used to verify SPE shape makes sense, and to see time evolution (the peak should occur at the same time across SPE)
    and drift once outside SPE range. For Run64922, for example, the SPE is ~27-40 mV.
    Frames -> Plots/Frames/, GIF -> Plots/
    """

    save_gif_path = Path(save_gif_path)

    plots_dir = save_gif_path.parent / "Plots"
    frames_dir = plots_dir / "Frames"

    plots_dir.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(parents=True, exist_ok=True)

    image_paths = []

    for midpoint in range(start, stop + 1, step):
        vmin = midpoint
        vmax = midpoint + bin_width

        groups = bin_waveforms_by_peak(
            clean_df,
            vmin,
            vmax,
            waveform_index_col=waveform_index_col
        )

        if not groups:
            continue

        t_bin, mean_bin, std_bin = interpolate_and_average(
            groups,
            num_points=num_points,
            x_end=x_end,
            max_waveforms=3000
        )

        if t_bin is None:
            continue
        # Scale normalized averages
        overall_scale = midpoint / (overall_mean.max() if overall_mean.max() != 0 else 1.0)
        overall_scaled = overall_mean * overall_scale
        overall_plus_scaled = overall_plus * overall_scale
        overall_minus_scaled = overall_minus * overall_scale

        bin_mean_mV = mean_bin * midpoint
        bin_plus_mV = (mean_bin + std_bin) * midpoint
        bin_minus_mV = (mean_bin - std_bin) * midpoint
        # Peak location of bin-averaged waveform
        peak_idx = np.argmax(bin_mean_mV)
        peak_t = t_bin[peak_idx]
        peak_v = bin_mean_mV[peak_idx]

        n_waveforms = len(groups)

        # Plot
        plt.figure(figsize=(10, 6))

        plt.plot(overall_t, overall_scaled, lw=2, label="Overall Avg (scaled)")
        plt.fill_between(
            overall_t,
            overall_minus_scaled,
            overall_plus_scaled,
            alpha=0.25,
            label="±1 STD (overall)"
        )

        plt.plot(t_bin, bin_mean_mV, lw=2, label=f"{vmin}–{vmax} mV bin")
        plt.fill_between(
            t_bin,
            bin_minus_mV,
            bin_plus_mV,
            alpha=0.2,
            label="±1 STD (bin)"
        )
        dt = 0.02 * x_end 
        dv = 0.04 * peak_v
        plt.plot(
        [peak_t - dt, peak_t + dt],
        [peak_v, peak_v],
        color="red",
        lw=1.5)

        plt.plot(
        [peak_t, peak_t],
        [peak_v - dv, peak_v + dv],
        color="red",
        lw=1.5)
        plt.text(
            0.02,
            0.95,
            f"N = {n_waveforms}",
            transform=plt.gca().transAxes,
            fontsize=12,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8)
            )

        plt.xlabel("Time (ns)")
        plt.ylabel("Voltage (mV)")
        plt.title(f"{vmin}–{vmax} mV vs Overall SPE")
        plt.legend()
        plt.grid(True)

        plt.xlim(0, x_end)
        plt.ylim(0, (stop + bin_width) * ylim_factor)

        frame_path = frames_dir / f"frame_{vmin}_{vmax}.png"
        plt.savefig(frame_path, bbox_inches="tight")
        plt.close()

        image_paths.append(frame_path)

    if not image_paths:
        print(f"  No frames produced for {save_gif_path.name}")
        return

    images = [imageio.imread(p) for p in image_paths]
    imageio.mimsave(save_gif_path, images, duration=1)

    # Cleanup frames
    for p in image_paths:
        try:
            os.remove(p)
        except Exception:
            pass

    print(f"  GIF saved to: {save_gif_path}")



def main():
    parser = argparse.ArgumentParser(description="Waveform analysis per channel with adjustable voltage ranges.")
    parser.add_argument("wfs_csv", help="wfs file with channel column (e.g. wfs_w_chan{run}.csv)")
    parser.add_argument("filtered_wfs_csv", help="filtered waveforms file (e.g. filtered_wfs_within_1_std{run}.csv)")
    parser.add_argument("--start", type=int, default=20, help="start voltage (mV) for bin midpoints")
    parser.add_argument("--stop", type=int, default=50, help="stop voltage (mV) for bin midpoints")
    parser.add_argument("--step", type=int, default=2, help="step (mV) between bin midpoints")
    parser.add_argument("--bin", dest="bin_width", type=int, default=2, help="bin width in mV (default 2)")
    parser.add_argument("--num_points", type=int, default=1000, help="number of interpolation points")
    parser.add_argument("--x_end", type=float, default=250.0, help="x-axis end (ns)")
    parser.add_argument("--outdir", type=str, default=".", help="output directory")
    parser.add_argument("--save-overall-csv", dest="save_overall_csv", action="store_true",
                        help="also save an overall normalized average CSV per channel from filtered waveforms")
    args = parser.parse_args()

    wfs_csv = args.wfs_csv
    filtered_wfs_csv = args.filtered_wfs_csv
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "Plots").mkdir(parents=True, exist_ok=True)

    run_number = extract_run_number(wfs_csv) or extract_run_number(filtered_wfs_csv) or "unknown"


    # Load CSVs
    print(f"Loading {wfs_csv} and {filtered_wfs_csv} ...")
    wfs = pd.read_csv(wfs_csv)
    filtered_wfs = pd.read_csv(filtered_wfs_csv)

    wfs = rm_column_spaces(wfs)
    filtered_wfs = rm_column_spaces(filtered_wfs)

    # Find waveform_index
    wf_idx_col = "waveform_index"
    if wf_idx_col not in wfs.columns:
        cand = find_waveform_index_col(wfs.columns)
        if cand:
            wfs = wfs.rename(columns={cand: wf_idx_col})
            print(f"Renamed waveform column '{cand}' -> '{wf_idx_col}' in wfs.")
        else:
            raise SystemExit("Error: no waveform index column found in wfs CSV")

    if wf_idx_col not in filtered_wfs.columns:
        cand = find_waveform_index_col(filtered_wfs.columns)
        if cand:
            filtered_wfs = filtered_wfs.rename(columns={cand: wf_idx_col})
            print(f"Renamed waveform column '{cand}' -> '{wf_idx_col}' in filtered_wfs.")
        else:
            raise SystemExit("Error: no waveform index column found in filtered_wfs CSV")

    if "chan" not in wfs.columns:
        print("Warning: 'chan' column not found in wfs. Attempting to proceed, but per-channel analysis requires 'chan'.")
        if "chan" in filtered_wfs.columns:
            wfs["chan"] = wfs[wf_idx_col].map(filtered_wfs.set_index(wf_idx_col)["chan"]).fillna(-1).astype(int)
            print("  Mapped chan from filtered_wfs into wfs where possible.")
        else:
            # single channel -> -1
            wfs["chan"] = -1

    # Columns are always written as "waveform_index, time (ns), voltage (mV)" by read_wf.cpp
    for col in ["waveform_index", "time (ns)", "voltage (mV)"]:
        if col not in wfs.columns:
            raise SystemExit(f"Error: expected column '{col}' not found in {wfs_csv}")

    channels = sorted(wfs["chan"].dropna().unique().tolist())
    print(f"Found channels: {channels}")

    for ch in channels:
        try:
            ch_int = int(ch)
        except Exception:
            ch_int = ch
        print(f"\nProcessing channel: {ch_int}")

        wfs_ch = wfs[wfs["chan"] == ch]
        filtered_wfs_ch = filtered_wfs[filtered_wfs["chan"] == ch]

        peak_df = (
            wfs_ch
            .groupby("waveform_index", sort=False)["voltage (mV)"]
            .max()
            .rename("peak_mV")
            .reset_index()
        )

        wfs_ch = wfs_ch.merge(peak_df, on="waveform_index", how="left")
        
        if filtered_wfs_ch.empty:
            print(f"  No filtered waveforms for channel {ch_int}, skipping.")
            continue

        overall = compute_overall_normalized_from_filtered(filtered_wfs_ch,
                                                            num_points=args.num_points,
                                                            x_end=args.x_end)

        if overall[0] is None:
            print(f"  Could not compute overall normalized waveform for channel {ch_int} (no groups).")
            continue

        overall_t, overall_mean, overall_std = overall
        overall_plus = overall_mean + overall_std
        overall_minus = overall_mean - overall_std
    
        if args.save_overall_csv:
            csv_out = outdir / f"norm_avg_waveform_R{run_number}_CH{ch_int}.csv"
            save_normalized_average_csv(overall_t, overall_mean, overall_std, csv_out)
            print(f"  Saved overall normalized CSV: {csv_out}")

        # GIF compares bin-averaged waveforms against the overall SPE shape using all (unfiltered) waveforms.
        # To restrict to filtered waveforms only, pass filtered_wfs_ch in place of wfs_ch.
        gif_out = outdir / "Plots" / f"SPE_isolation_R{run_number}_CH{ch_int}.gif"

        create_comparison_gif_per_channel(
            clean_df=wfs_ch,
            overall_t=overall_t,
            overall_mean=overall_mean,
            overall_plus=overall_plus,
            overall_minus=overall_minus,
            save_gif_path=gif_out,
            start=args.start,
            stop=args.stop,
            step=args.step,
            bin_width=args.bin_width,
            num_points=args.num_points,
            x_end=args.x_end,
            waveform_index_col=wf_idx_col
        )

    print("\nAll channels processed. Outputs written to:", outdir)

if __name__ == "__main__":
    main()