#!/usr/bin/env bash
# -----------------------------------------------------------------------------
#  Copyright (c) NoMercy Entertainment
#
#  Licensed under the Apache License, Version 2.0. See LICENSE for details.
#
#  SPDX-License-Identifier: Apache-2.0
# -----------------------------------------------------------------------------

# One-time WSL setup: build the patched Tesseract (NoMercy fork, append-index
# fix) with training tools into $HOME/tesseract-install — the same prefix CI
# uses on beast-unit. Idempotent: skips the build if lstmtraining exists.
set -euo pipefail

if [ -x "$HOME/tesseract-install/bin/lstmtraining" ]; then
  echo "Patched Tesseract already built at $HOME/tesseract-install"
  "$HOME/tesseract-install/bin/tesseract" --version | head -2
  exit 0
fi

sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
  g++ cmake make pkg-config git \
  libleptonica-dev libicu-dev libpango1.0-dev libcairo2-dev \
  fonts-noto fonts-noto-cjk fonts-noto-cjk-extra fonts-noto-extra \
  fonts-noto-ui-core fonts-noto-core fonts-noto-unhinted \
  fonts-dejavu fonts-liberation fontconfig wget python3 python3-pip

rm -rf "$HOME/tesseract-src"
git clone --depth 1 --branch fix/append-index-lstmrecognizer \
  https://github.com/NoMercy-Entertainment/tesseract.git "$HOME/tesseract-src"
cd "$HOME/tesseract-src"
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_TRAINING_TOOLS=ON \
  -DCMAKE_INSTALL_PREFIX="$HOME/tesseract-install"
make -j"$(nproc)"
make install
sudo ldconfig
# Pillow for rendering; python-bidi for RTL/Indic word-string boxing.
pip3 install --quiet --break-system-packages Pillow python-bidi 2>/dev/null || pip3 install --quiet Pillow python-bidi

"$HOME/tesseract-install/bin/tesseract" --version | head -2
echo "Setup complete."
