#!/bin/bash
# Download the prebuilt gnina binary (no compiling). Run on gandalf (login node).
set -e

mkdir -p ~/hackathon/bin
cd ~/hackathon/bin
wget -O gnina https://github.com/gnina/gnina/releases/latest/download/gnina
chmod +x gnina

echo ""
echo "Installed. Version check:"
./gnina --version || echo "  (version check failed -- may need a GPU allocation for CUDA libs; try inside srun)"
