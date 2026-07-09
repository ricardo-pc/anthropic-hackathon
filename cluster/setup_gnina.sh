#!/bin/bash
# Download the prebuilt gnina binary (no compiling). Run on gandalf (login node).
# NOTE: the binary is ~2 GB and the SCF HOME directory (/accounts/...) is quota-limited,
# so it goes on /scratch (where the conda env already lives), symlinked into ~/hackathon/bin.
set -e

SCRATCH_BIN="/scratch/users/$USER/bin"
mkdir -p "$SCRATCH_BIN" ~/hackathon/bin
cd "$SCRATCH_BIN"
# v1.3.3's only asset is a CUDA 12.8 static build -- matches roo's CUDA 12.8 exactly,
# so gnina's GPU CNN scoring works. (The generic name `gnina` 404s; the asset is versioned.)
wget -O gnina https://github.com/gnina/gnina/releases/download/v1.3.3/gnina.cuda12.8.static
chmod +x gnina
ln -sf "$SCRATCH_BIN/gnina" ~/hackathon/bin/gnina  # scripts reference ~/hackathon/bin/gnina

echo ""
echo "Installed. Version check:"
./gnina --version || echo "  (version check failed -- may need a GPU allocation for CUDA libs; try inside srun)"
