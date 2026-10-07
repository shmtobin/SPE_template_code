Hello! My name is Shane Tobin and I worked on the MilliQan experiment under Professor Stuart in 2025. To document my work in the hopes it helps progress this project, I have created this repository. Below I will explain how to use the scripts. In sections where a future user may need to modify the script to run the code from their own cmsX account. If you have any questions, feel free to reach out and I'd be happy to chat about this project.

# Pipeline

This directory contains the automated analysis pipeline for processing DRS waveform and pulse data for a given run.

The pipeline downloads the raw data files for a run, converts the raw `.ant` files into CSV files using C++, performs pulse-level analysis in Python, filters the pulse population, associates the surviving pulses with their corresponding waveforms, and performs waveform analysis and SPE-shape comparisons.

The pipeline is designed to operate on runs with a consistent input and file format.

---

## Overview

The pipeline consists of four primary stages:

1. **Download raw data**

   * Download the pulse and waveform `.ant` files for the requested run from the remote data server.

2. **Convert raw `.ant` files to CSV**

   * `read_pulse.cpp` converts the pulse data into `Run<run>_mqspulses.csv`.
   * `read_WF.cpp` converts the waveform data into `Run<run>_waveforms.csv`.

3. **Pulse analysis**

   * `pulse_analysis.py` associates each waveform with its corresponding pulse and channel.
   * Saturated pulses are removed.
   * A linear pulse-height vs. pulse-area fit is performed independently for each channel.
   * Pulses outside ±1 standard deviation of the channel fit are removed.
   * The corresponding waveform records are retained.

4. **Waveform analysis**

   * `waveform_analysis.py` analyzes the filtered waveforms by channel.
   * Waveforms are normalized to their peak voltage.
   * Average waveforms and standard deviations are calculated.
   * Voltage-binned waveform averages are compared with the overall waveform using GIFs.

---

## Directory Structure

The expected project structure is:

```text
project_root/
├── Pipeline/
│   ├── run_pipeline.sh
│   ├── read_pulse.cpp
│   ├── read_WF.cpp
│   ├── pulse_analysis.py
│   ├── waveform_analysis.py
│   └── requirements.txt
│
├── .venv/
│   └── ...
│
└── README.md
```

Running `run_pipeline.sh` creates a run-specific working directory in the location from which the script is executed.

For example:

```text
Run64922/
├── Run64922_mqspulses.ant
├── Run64922_WF.ant
├── Run64922_mqspulses.csv
├── Run64922_waveforms.csv
├── wfs_w_chan64922.csv
├── filtered_wfs_within_1_std64922.csv
├── read_pulse
├── read_wf
└── Plots/
    ├── pulse_height_vs_area_run64922.png
    ├── pulse_height_vs_area_run64922_CH1.png
    ├── pulse_height_vs_area_run64922_CH2.png
    ├── ...
    └── SPE_isolation_R64922_CH1.gif
```

---

# Requirements

## Operating System

The pipeline is intended to run in a Unix-like environment with access to:

* Bash
* Python 3
* `g++`
* `scp`
* `gunzip`

The environment must also be able to connect to the remote server containing the raw DRS data.

---

## C++ Compiler

The C++ programs require a compiler supporting C++11 or later.

The pipeline compiles them using:

```bash
g++ -O2 -std=c++11
```

---

## Python

Python 3 is required.

The pipeline automatically creates a virtual environment named:

```text
.venv/
```

in the project root if one does not already exist.

Python dependencies are installed from:

```text
requirements.txt
```

---

## Remote Data Access

The pipeline retrieves raw files using `scp` from:

```text
shanetobin@cms1.physics.ucsb.edu:/cms1r0/stuart/DRS/Run<run_number>/
```

[Substitute your account username in the code] Which I anticipate will be substituted 

The expected raw files are:

```text
Run<run_number>_mqspulses.ant
Run<run_number>_WF.ant.gz
```

The machine running the pipeline must therefore have SSH access to:

```text
cms1.physics.ucsb.edu
```

and the appropriate credentials/configuration for `scp`.

---

# Input Data Format

The pipeline assumes a fixed input format.

## Pulse Data

The raw pulse file is:

```text
Run<run_number>_mqspulses.ant
```

`read_pulse.cpp` expects each valid line to contain the pulse fields in the following order:

```text
run
evt
chan
V
area
time
fittime
fitdtime
halftime
fitslope
fitnpoints
fitprob
ipulse
width
sidebandMean
sidebandRMS
qual
risetime
falltime
premean
prerms
```

The resulting CSV has the header:

```text
run,evt,chan,V,area,time,fittime,fitdtime,halftime,fitslope,fitnpoints,fitprob,ipulse,width,sidebandMean,sidebandRMS,qual,risetime,falltime,premean,prerms
```

---

## Waveform Data

The raw waveform file is:

```text
Run<run_number>_WF.ant
```

This file is compressed on the remote server and is downloaded as:

```text
Run<run_number>_WF.ant.gz
```

The pipeline decompresses it to:

```text
Run<run_number>_WF.ant
```

`read_WF.cpp` converts the waveform file into:

```text
Run<run_number>_waveforms.csv
```

with the fixed header:

```text
waveform_index, time (ns), voltage (mV)
```

The waveform index is assigned sequentially by the C++ waveform reader.

---

# Running the Pipeline

The complete pipeline is executed using:

```bash
./Pipeline/run_pipeline.sh <run_number>
```

For example:

```bash
./Pipeline/run_pipeline.sh 64922
```

The run number should be provided without the `Run` prefix.

Correct:

```bash
./Pipeline/run_pipeline.sh 64922
```

Not:

```bash
./Pipeline/run_pipeline.sh Run64922
```

---

# Making the Script Executable

If necessary, make the pipeline script executable:

```bash
chmod +x Pipeline/run_pipeline.sh
```

Then run:

```bash
./Pipeline/run_pipeline.sh 64922
```

---

# Pipeline Execution

When the pipeline is run for a new run, it performs the following operations.

## 1. Create the Run Directory

A directory named:

```text
Run<run_number>
```

is created.

For example:

```text
Run64922/
```

A `Plots/` directory is also created inside the run directory.

---

## 2. Download Pulse Data

The pipeline checks whether:

```text
Run<run_number>_mqspulses.ant
```

already exists.

If it does not, it downloads the file from the remote DRS data directory.

If the file already exists, the download is skipped.

---

## 3. Download and Decompress Waveform Data

The pipeline checks whether:

```text
Run<run_number>_WF.ant
```

already exists.

If it does not, it downloads:

```text
Run<run_number>_WF.ant.gz
```

and decompresses it to:

```text
Run<run_number>_WF.ant
```

The compressed file is removed after successful decompression.

---

## 4. Compile the C++ Readers

The pipeline compiles the two C++ programs when their executables do not already exist:

```text
read_pulse
read_wf
```

The commands used are equivalent to:

```bash
g++ -O2 -std=c++11 ../read_pulse.cpp -o read_pulse
g++ -O2 -std=c++11 ../read_WF.cpp -o read_wf
```

---

## 5. Convert Raw Data to CSV

The pulse reader is run as:

```bash
./read_pulse <run_number>
```

This produces:

```text
Run<run_number>_mqspulses.csv
```

The waveform reader is run as:

```bash
./read_wf <run_number>
```

This produces:

```text
Run<run_number>_waveforms.csv
```

The pipeline skips either conversion if the corresponding CSV already exists.

---

## 6. Create and Activate the Python Environment

If the project virtual environment does not already exist, the pipeline creates it:

```bash
python3 -m venv ../.venv
```

It then activates the environment and installs the required packages:

```bash
pip install --upgrade pip
pip install -r ../requirements.txt
```

---

# Pulse Analysis

After generating the two CSV files, the pipeline runs:

```bash
python3 ../pulse_analysis.py \
    "Run<run_number>_mqspulses.csv" \
    "Run<run_number>_waveforms.csv"
```

For example:

```bash
python3 ../pulse_analysis.py \
    "Run64922_mqspulses.csv" \
    "Run64922_waveforms.csv"
```

## Waveform/Channel Association

The pulse CSV does not contain a waveform index.

The pipeline relies on the fact that the C++ pulse and waveform readers generate their outputs in the same order.

The pulse dataframe index is therefore used as the waveform index:

```text
pulse index 0  -> waveform_index 0
pulse index 1  -> waveform_index 1
pulse index 2  -> waveform_index 2
...
```

The corresponding channel is then transferred from the pulse dataframe to the waveform dataframe.

This ordering relationship is a required assumption of the pipeline.

---

## Pulse Filtering

The pulse analysis performs the following selection:

### Saturation Cut

Pulses with:

```text
V >= 200
```

are removed.

The retained pulses satisfy:

```text
V < 200
```

---

## Channel-by-Channel Linear Fit

For each channel, the pipeline fits:

```text
area = slope × V + intercept
```

using a first-order polynomial fit.

The residual for each pulse is calculated as:

```text
residual = measured_area - fitted_area
```

The standard deviation of the residuals is then calculated independently for each channel.

---

## ±1σ Pulse Selection

Only pulses satisfying:

```text
|residual| <= standard_deviation
```

are retained.

The waveform indices belonging to these surviving pulses are then used to select the corresponding waveforms.

The resulting filtered waveform file is:

```text
filtered_wfs_within_1_std<run_number>.csv
```

For example:

```text
filtered_wfs_within_1_std64922.csv
```

---

# Pulse Analysis Outputs

The pulse analysis produces:

```text
wfs_w_chan<run_number>.csv
```

This file contains the waveform data with channel information added.

It also produces:

```text
filtered_wfs_within_1_std<run_number>.csv
```

containing the waveforms corresponding to pulses surviving the pulse-height/area filtering.

---

## Pulse Analysis Plots

The pulse analysis creates a combined pulse-height vs. pulse-area plot:

```text
Plots/pulse_height_vs_area_run<run_number>.png
```

It also creates one plot per channel:

```text
Plots/pulse_height_vs_area_run<run_number>_CH<channel>.png
```

These plots show:

* pulse-height vs. pulse-area measurements
* the best-fit linear relationship
* the +1σ residual boundary
* the −1σ residual boundary

---

# Waveform Analysis

The second Python stage is run using:

```bash
python3 ../waveform_analysis.py \
    "wfs_w_chan<run_number>.csv" \
    "filtered_wfs_within_1_std<run_number>.csv"
```

For example:

```bash
python3 ../waveform_analysis.py \
    "wfs_w_chan64922.csv" \
    "filtered_wfs_within_1_std64922.csv"
```

---

# Waveform Normalization

Waveforms are processed independently for each channel.

For each waveform:

1. The waveform time axis is shifted so that its first sample occurs at:

   ```text
   t = 0 ns
   ```

2. The waveform is normalized to its maximum voltage.

3. The normalized waveform is interpolated onto a common time axis.

4. The average waveform and standard deviation are calculated.

The default common time axis contains:

```text
1000 points
```

from:

```text
0 ns to 250 ns
```

---

# Voltage-Binned Waveform Analysis

The waveform analysis groups waveforms according to their peak voltage.

The default voltage-bin parameters are:

```text
Start:       20 mV
Stop:        50 mV
Step:         2 mV
Bin width:    2 mV
```

These can be changed from the command line.

For example:

```bash
python3 ../waveform_analysis.py \
    "wfs_w_chan64922.csv" \
    "filtered_wfs_within_1_std64922.csv" \
    --start 20 \
    --stop 60 \
    --step 2 \
    --bin 2
```

---

# Waveform Analysis Outputs

For each channel, the pipeline produces a comparison GIF:

```text
Plots/SPE_isolation_R<run_number>_CH<channel>.gif
```

For example:

```text
Plots/SPE_isolation_R64922_CH1.gif
```

Each frame compares:

* the overall normalized average waveform
* the overall ±1σ variation
* the voltage-binned average waveform
* the voltage-binned ±1σ variation

The GIF also displays the location of the peak waveform voltage.

---

# Optional Overall Waveform CSV

The waveform analysis supports an optional argument:

```bash
--save-overall-csv
```

When supplied, a normalized average waveform CSV is produced for each channel:

```text
norm_avg_waveform_R<run_number>_CH<channel>.csv
```

For example:

```bash
python3 ../waveform_analysis.py \
    "wfs_w_chan64922.csv" \
    "filtered_wfs_within_1_std64922.csv" \
    --save-overall-csv
```

---

# Command-Line Options

`waveform_analysis.py` accepts the following optional arguments:

| Argument             |  Default | Description                               |
| -------------------- | -------: | ----------------------------------------- |
| `--start`            |     `20` | Starting voltage for bins, in mV          |
| `--stop`             |     `50` | Ending voltage for bins, in mV            |
| `--step`             |      `2` | Voltage step between bins, in mV          |
| `--bin`              |      `2` | Width of each voltage bin, in mV          |
| `--num_points`       |   `1000` | Number of points in interpolated waveform |
| `--x_end`            |    `250` | End of common time axis, in ns            |
| `--outdir`           |      `.` | Output directory                          |
| `--save-overall-csv` | disabled | Save normalized average waveform CSVs     |

---

# Re-running a Run

The pipeline is designed to avoid repeating completed work.

At startup, it checks whether:

```text
filtered_wfs_within_1_std<run_number>.csv
```

already exists.

If the final output exists, the pipeline exits immediately and reports that the run has already been processed.

Individual stages also check for their expected output files and skip processing when those files already exist.

To force a run to be processed again, remove the relevant output files or remove the entire run directory.

For example:

```bash
rm -rf Run64922
```

Then rerun:

```bash
./Pipeline/run_pipeline.sh 64922
```

Use caution when deleting run directories, since this removes both raw downloaded files and generated analysis products.

---

# Running Individual Pipeline Stages

The individual programs can also be run manually for debugging or development.

## C++ Pulse Reader

From inside the run directory:

```bash
./read_pulse <run_number>
```

Example:

```bash
./read_pulse 64922
```

---

## C++ Waveform Reader

From inside the run directory:

```bash
./read_wf <run_number>
```

Example:

```bash
./read_wf 64922
```

---

## Pulse Analysis

From inside the run directory:

```bash
python3 ../pulse_analysis.py \
    "Run<run_number>_mqspulses.csv" \
    "Run<run_number>_waveforms.csv"
```

---

## Waveform Analysis

From inside the run directory:

```bash
python3 ../waveform_analysis.py \
    "wfs_w_chan<run_number>.csv" \
    "filtered_wfs_within_1_std<run_number>.csv"
```

---

# Important Pipeline Assumptions

The pipeline intentionally assumes a consistent input and output structure.

These assumptions are important and should not be changed without modifying the downstream analysis.

## 1. Pulse and Waveform Ordering

The pulse and waveform C++ readers must produce records in the same order.

The pulse dataframe index is used as the waveform index.

Therefore:

```text
pulse row N ↔ waveform_index N
```

must remain true.

---

## 2. Fixed CSV Column Names

The C++ programs generate fixed CSV schemas.

The waveform CSV must contain:

```text
waveform_index
time (ns)
voltage (mV)
```

The pulse CSV must contain:

```text
run
evt
chan
V
area
time
fittime
fitdtime
halftime
fitslope
fitnpoints
fitprob
ipulse
width
sidebandMean
sidebandRMS
qual
risetime
falltime
premean
prerms
```

---

## 3. Run-Based File Naming

Files are expected to follow the naming convention:

```text
Run<run_number>_mqspulses.ant
Run<run_number>_WF.ant
Run<run_number>_mqspulses.csv
Run<run_number>_waveforms.csv
wfs_w_chan<run_number>.csv
filtered_wfs_within_1_std<run_number>.csv
```

Changing these naming conventions requires corresponding changes to the pipeline scripts.

---

# Troubleshooting

## SSH/SCP Errors

If the raw files cannot be downloaded, verify that the machine can connect to the remote server:

```bash
ssh shanetobin@cms1.physics.ucsb.edu
```

Also verify that the expected run directory exists on the remote server.

---

## Missing C++ Compiler

Check that `g++` is installed:

```bash
g++ --version
```

The compiler must support C++11.

---

## Python Dependency Errors

The pipeline uses a project virtual environment.

To recreate the environment manually:

```bash
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Missing Input Files

Verify that the expected files exist inside the run directory:

```bash
ls -lh Run<run_number>*
```

---

## Unexpected Empty Output

If the filtered waveform file contains no waveforms, check the pulse-height vs. pulse-area plot:

```text
Plots/pulse_height_vs_area_run<run_number>.png
```

The ±1σ cut is applied independently for each channel. A channel with too few usable pulses cannot produce a fit and will therefore not contribute to the filtered output.

---

# Development Notes

The pipeline is intended to be deterministic for a given run and input dataset.

The C++ programs define the raw-data-to-CSV interface, while the Python programs operate on those generated CSV files.

When modifying the pipeline, preserve the expected file naming, column naming, and pulse/waveform ordering conventions unless all dependent stages are updated accordingly.

The `run_pipeline.sh` script should generally be considered the primary entry point for production processing, while the individual C++ and Python programs can be run directly when debugging or developing individual stages.

---

# Example Complete Run

A typical processing command is:

```bash
./Pipeline/run_pipeline.sh 64922
```

A successful run should ultimately produce:

```text
Run64922/
├── Run64922_mqspulses.ant
├── Run64922_WF.ant
├── Run64922_mqspulses.csv
├── Run64922_waveforms.csv
├── wfs_w_chan64922.csv
├── filtered_wfs_within_1_std64922.csv
├── read_pulse
├── read_wf
└── Plots/
    ├── pulse_height_vs_area_run64922.png
    ├── pulse_height_vs_area_run64922_CH1.png
    ├── pulse_height_vs_area_run64922_CH2.png
    ├── pulse_height_vs_area_run64922_CH3.png
    ├── pulse_height_vs_area_run64922_CH4.png
    ├── SPE_isolation_R64922_CH1.gif
    ├── SPE_isolation_R64922_CH2.gif
    ├── SPE_isolation_R64922_CH3.gif
    └── SPE_isolation_R64922_CH4.gif
```

The primary final data product used by downstream analysis is:

```text
filtered_wfs_within_1_std<run_number>.csv
```

while the plots in `Plots/` provide diagnostic information about the pulse selection and waveform behavior.