#!/bin/bash
# Run ON gandalf (the SCF login node), NOT inside a GPU allocation — this just
# installs software and doesn't need the GPU yet. Safe to run on the login node.
set -e

cd ~
if [ ! -d DiffDock ]; then
    git clone https://github.com/gcorso/DiffDock.git
fi
cd DiffDock

conda env create --file environment.yml || conda env update --file environment.yml

# environment.yml has a known upstream bug: it defines THREE separate `pip:` blocks
# under `dependencies:`. Conda only honors the LAST one, so torch/e3nn/torch-geometric
# (block 1) and openfold (block 2) silently never install -- only gradio (block 3) does.
# Verify and patch if needed:
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate diffdock

if ! python -c "import torch" 2>/dev/null; then
    echo "torch missing (expected -- known environment.yml bug). Installing dropped block 1..."
    pip install \
      --extra-index-url https://download.pytorch.org/whl/cu117 \
      --find-links https://pytorch-geometric.com/whl/torch-1.13.1+cu117.html \
      torch==1.13.1+cu117 \
      dllogger@git+https://github.com/NVIDIA/dllogger.git \
      e3nn==0.5.1 \
      "fair-esm[esmfold]==2.0.0" \
      networkx==2.8.4 \
      pandas==1.5.1 \
      pybind11==2.11.1 \
      pytorch-lightning==1.9.5 \
      rdkit==2022.03.3 \
      scikit-learn==1.1.0 \
      torch-cluster==1.6.0+pt113cu117 \
      torch-geometric==2.2.0 \
      torch-scatter==2.1.0+pt113cu117 \
      torch-sparse==0.6.16+pt113cu117 \
      torch-spline-conv==1.2.1+pt113cu117 \
      torchmetrics==0.11.0
fi

if ! python -c "import openfold" 2>/dev/null; then
    echo "openfold missing (expected -- known environment.yml bug). Installing dropped block 2..."
    pip install "openfold@git+https://github.com/aqlaboratory/openfold.git@4b41059694619831a7db195b7e0988fc4ff3a307"
fi

echo ""
echo "Done. Activate with:  conda activate diffdock"
