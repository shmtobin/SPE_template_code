#!/usr/bin/env bash
# run_pipeline.sh: full analysis pipeline for a given run number

set -euo pipefail

# Usage check
if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <run_number>"
  exit 1
fi

RNUM="$1"
DIR="Run${RNUM}"

# Prompt for cleanup preference
echo "After the pipeline completes, which files would you like to keep?"
echo "  1) All output files (keep everything except .ant files and intermediate CSVs)"
echo "  2) Minimal: keep only filtered_wfs_within_1_std${RNUM}.csv (and all Plots/GIFs)"
read -rp "Enter 1 or 2: " KEEP_MODE
if [[ "$KEEP_MODE" != "1" && "$KEEP_MODE" != "2" ]]; then
  echo "Invalid selection. Please enter 1 or 2."
  exit 1
fi

# 1) Check if final output already exists
FINAL_OUTPUT="${DIR}/filtered_wfs_within_1_std${RNUM}.csv"
if [[ -f "$FINAL_OUTPUT" ]]; then
  echo "Run ${RNUM} has already been processed. Output file exists: $FINAL_OUTPUT"
  exit 0
fi

# 2) Create workspace and Plots directory
mkdir -p "${DIR}"
cd "${DIR}"
mkdir -p Plots

echo "Downloading data for Run${RNUM}..."

# 3) Download .ant files
if [[ ! -f "Run${RNUM}_mqspulses.ant" ]]; then
  scp shanetobin@cms1.physics.ucsb.edu:/cms1r0/stuart/DRS/Run${RNUM}/Run${RNUM}_mqspulses.ant .
else
  echo "File Run${RNUM}_mqspulses.ant already exists — skipping download."
fi

# 4) Download & decompress WF file
if [[ ! -f "Run${RNUM}_WF.ant" ]]; then
  echo "Downloading Run${RNUM}_WF.ant.gz..."
  scp shanetobin@cms1.physics.ucsb.edu:/cms1r0/stuart/DRS/Run${RNUM}/Run${RNUM}_WF.ant.gz .
  echo "Decompressing..."
  gunzip -c "Run${RNUM}_WF.ant.gz" > "Run${RNUM}_WF.ant"
  rm "Run${RNUM}_WF.ant.gz"
else
  echo "File Run${RNUM}_WF.ant already exists — skipping download."
fi


if [[ ! -x read_pulse ]]; then
  echo "Compiling read_pulse..."
  g++ -O2 -std=c++11 "../read_pulse.cpp" -o read_pulse
else
  echo "read_pulse already compiled."
fi

if [[ ! -x read_wf ]]; then
  echo "Compiling read_wf..."
  g++ -O2 -std=c++11 "../read_wf.cpp" -o read_wf
else
  echo "read_wf already compiled."
fi

# 5) Run C++ scripts
if [[ ! -f "Run${RNUM}_waveforms.csv" ]]; then
  echo "Running waveform converter..."
  ./read_wf "${RNUM}"
else
  echo "Run${RNUM}_waveforms.csv already exists — skipping."
fi

if [[ ! -f "Run${RNUM}_mqspulses.csv" ]]; then
  echo "Running pulse converter..."
  ./read_pulse "${RNUM}"
else
  echo "Run${RNUM}_mqspulses.csv already exists — skipping."
fi

# ensure Python venv and required packages are available
VENV="../.venv"
if [[ ! -d "$VENV" ]]; then
  python3 -m venv "$VENV"
fi

source "$VENV/bin/activate"
pip install --upgrade pip
pip install -r ../requirements.txt

# 6) Run Python analysis
if [[ ! -f "wfs_w_chan${RNUM}.csv" || ! -f "filtered_wfs_within_1_std${RNUM}.csv" ]]; then
  echo "Running pulse analysis..."
  python3 ../pulse_analysis.py \
    "Run${RNUM}_mqspulses.csv" \
    "Run${RNUM}_waveforms.csv"
    
  echo "Running waveform analysis..."
  python3 ../waveform_analysis.py \
    "wfs_w_chan${RNUM}.csv" \
    "filtered_wfs_within_1_std${RNUM}.csv"
else
  echo "Python analysis outputs already exist — skipping."
fi

echo "Pipeline complete. Outputs in ${DIR}."

echo "Cleaning up intermediate files..."
rm -rf \
  "Run${RNUM}_mqspulses.ant" \
  "Run${RNUM}_WF.ant" \
  "Run${RNUM}_mqspulses.csv" \
  "Run${RNUM}_waveforms.csv" \
  "wfs_w_chan${RNUM}.csv"

if [[ "$KEEP_MODE" == "2" ]]; then
  echo "Minimal mode: removing all outputs except filtered_wfs_within_1_std${RNUM}.csv and Plots..."
  find . -maxdepth 1 -type f \
    ! -name "filtered_wfs_within_1_std${RNUM}.csv" \
    -exec rm -rf {} +
fi