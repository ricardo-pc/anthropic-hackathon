#!/bin/bash
# Download the prebuilt gnina binary (no compiling). Run on gandalf (login node).
set -e

mkdir -p ~/hackathon/bin
cd ~/hackathon/bin
# v1.3.3's only asset is a CUDA 12.8 static build -- which matches roo's CUDA 12.8 exactly,
# so gnina's GPU CNN scoring will work. (The generic name `gnina` 404s; the asset is versioned.)
# ~2 GB download.
wget -O gnina https://github.com/gnina/gnina/releases/download/v1.3.3/gnina.cuda12.8.static
chmod +x gnina

echo ""
echo "Installed. Version check:"
./gnina --version || echo "  (version check failed -- may need a GPU allocation for CUDA libs; try inside srun)"
