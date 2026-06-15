#!/usr/bin/env bash
# -----------------------------------------------------------------------------
#  Copyright (c) NoMercy Entertainment
#
#  Licensed under the Apache License, Version 2.0. See LICENSE for details.
#
#  SPDX-License-Identifier: Apache-2.0
# -----------------------------------------------------------------------------

# Local mirror of .github/workflows/train.yml — fast iteration before CI.
# Runs in WSL Ubuntu against the patched Tesseract at $HOME/tesseract-install.
#
# Usage (from WSL, repo root):
#   LANG_CODE=swe MAX_ITERATIONS=400 MAX_LINES=200 bash training/local/run-train.sh
#
# Knobs:
#   LANG_CODE       language to train (required)
#   MAX_ITERATIONS  lstmtraining iterations (default 400 — short smoke run)
#   MAX_LINES       ground-truth lines to render (default 200 — short smoke run)
#
# Output goes to training/local/out/$LANG_CODE.traineddata — it never touches
# tessdata/, so a smoke run can't clobber a shipped model. CI is the only path
# that writes tessdata/ and commits.
set -euo pipefail

LANG_CODE="${LANG_CODE:?set LANG_CODE}"
MAX_ITERATIONS="${MAX_ITERATIONS:-400}"
MAX_LINES="${MAX_LINES:-200}"
MODEL="$LANG_CODE"

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_REPO="$REPO/training/local/out"
WORK="/tmp/tess-local-$LANG_CODE"
TESSDATA="$WORK/usr/share/tessdata"
GT_DIR="$WORK/data/${MODEL}-ground-truth"
OUTPUT_DIR="$WORK/data/$MODEL"
LANGDATA_DIR="$WORK/data/langdata"

export PATH="$HOME/tesseract-install/bin:$PATH"
export LD_LIBRARY_PATH="$HOME/tesseract-install/lib:${LD_LIBRARY_PATH:-}"
export TESSDATA_PREFIX="$TESSDATA"

command -v lstmtraining >/dev/null || { echo "ERROR: patched Tesseract not built — run training/local/setup-wsl.sh"; exit 1; }

echo "== $MODEL | iters=$MAX_ITERATIONS | lines=$MAX_LINES =="
rm -rf "$WORK"
mkdir -p "$TESSDATA" "$GT_DIR" "$OUTPUT_DIR/checkpoints" "$LANGDATA_DIR/$MODEL" "$OUT_REPO"

if [ ! -d /tmp/tesstrain-shared ]; then
  git clone --depth 1 https://github.com/tesseract-ocr/tesstrain.git /tmp/tesstrain-shared
fi
TESSTRAIN=/tmp/tesstrain-shared

echo "-- render ground-truth"
TRAINING_TEXT="$REPO/training/generated/$MODEL/$MODEL.training_text"
FONTS_FILE="$REPO/training/generated/$MODEL/$MODEL.fonts"
[ -f "$TRAINING_TEXT" ] || { echo "ERROR: no training text at $TRAINING_TEXT"; exit 1; }
[ -f "$FONTS_FILE" ] || echo "DejaVu Sans" > "$FONTS_FILE"
python3 "$REPO/training/scripts/render_diverse.py" \
  --training-text "$TRAINING_TEXT" --fonts-file "$FONTS_FILE" \
  --out-dir "$GT_DIR" --lang "$MODEL" --max-lines "$MAX_LINES" --workers "$(nproc)"
for png in "$REPO"/training/ground-truth/${MODEL}_*.png; do
  [ -f "$png" ] || continue
  stem=$(basename "${png%.png}"); cp "$png" "$GT_DIR/${stem}.png"
  gt="${png%.png}.gt.txt"; [ -f "$gt" ] && cp "$gt" "$GT_DIR/${stem}.gt.txt"
done
[ "$(find "$GT_DIR" -name '*.gt.txt' | wc -l)" -gt 0 ] || { echo "ERROR: no GT rendered"; exit 1; }

echo "-- fetch tessdata_best/$MODEL"
cp -r "$HOME"/tesseract-install/share/tessdata/configs "$TESSDATA/" 2>/dev/null || true
cp -r "$HOME"/tesseract-install/share/tessdata/tessconfigs "$TESSDATA/" 2>/dev/null || true
wget -q -O "$TESSDATA/$MODEL.traineddata" \
  "https://github.com/tesseract-ocr/tessdata_best/raw/main/$MODEL.traineddata" \
  || { echo "ERROR: $MODEL not in tessdata_best — cannot fine-tune"; exit 1; }

echo "-- validate pairs (box files)"
find "$GT_DIR" -maxdepth 1 -name '*.gt.txt' -print0 | xargs -0 -P "$(nproc)" -I {} bash -c '
  gt="{}"; STEM="${gt%.gt.txt}"; IMG=""
  for e in png tif tiff; do [ -f "${STEM}.${e}" ] && [ "$(wc -c < "${STEM}.${e}")" -ge 200 ] && IMG="${STEM}.${e}" && break; done
  [ -z "$IMG" ] && { rm -f "${STEM}".gt.txt "${STEM}".png "${STEM}".tif "${STEM}".tiff; exit 0; }
  python3 "'"$TESSTRAIN"'/generate_line_box.py" -i "$IMG" -t "${STEM}.gt.txt" > "${STEM}.box" 2>/dev/null
  [ -s "${STEM}.box" ] || rm -f "${STEM}".gt.txt "${STEM}".png "${STEM}".box'
[ "$(find "$GT_DIR" -name '*.gt.txt' | wc -l)" -gt 0 ] || { echo "ERROR: no valid GT after boxing"; exit 1; }

echo "-- langdata"
wget -q -O "$LANGDATA_DIR/radical-stroke.txt" \
  "https://github.com/tesseract-ocr/langdata_lstm/raw/main/radical-stroke.txt" || true
for script in Latin Cyrillic Greek Arabic Hebrew Devanagari Bengali Tamil Telugu \
              Kannada Malayalam Gujarati Gurmukhi Thai Khmer Lao Myanmar Sinhala \
              Ethiopic Georgian Armenian Han Hiragana Katakana Hangul Bopomofo \
              Canadian_Aboriginal Cherokee Ogham Oriya Runic Syriac; do
  wget -q -O "$LANGDATA_DIR/${script}.unicharset" \
    "https://github.com/tesseract-ocr/langdata_lstm/raw/main/${script}.unicharset" 2>/dev/null || true
done
: > "$OUTPUT_DIR/$MODEL.wordlist"; : > "$OUTPUT_DIR/$MODEL.punc"; : > "$OUTPUT_DIR/$MODEL.numbers"

echo "-- phase 1: lstmf"
find "$GT_DIR" -maxdepth 1 -name '*.gt.txt' -print0 | xargs -0 -P "$(nproc)" -I {} bash -c '
  gt="{}"; STEM="${gt%.gt.txt}"; IMG=""
  for e in png tif tiff; do [ -f "${STEM}.${e}" ] && IMG="${STEM}.${e}" && break; done
  [ -z "$IMG" ] && exit 0; [ ! -f "${STEM}.box" ] && exit 0
  tesseract "$IMG" "$STEM" --psm 13 -l "'"$MODEL"'" lstm.train 2>/dev/null || true'
find "$GT_DIR" -maxdepth 1 -name '*.lstmf' > "$OUTPUT_DIR/all-lstmf"
TOTAL=$(wc -l < "$OUTPUT_DIR/all-lstmf")
[ "$TOTAL" -gt 0 ] || { echo "ERROR: no lstmf generated"; exit 1; }
( cd "$TESSTRAIN" && python3 shuffle.py 0 "$OUTPUT_DIR/all-lstmf" )
TRAIN_SIZE=$(( TOTAL * 90 / 100 )); [ "$TRAIN_SIZE" -lt 1 ] && TRAIN_SIZE=1
head -n "$TRAIN_SIZE" "$OUTPUT_DIR/all-lstmf" > "$OUTPUT_DIR/list.train"
tail -n +"$((TRAIN_SIZE + 1))" "$OUTPUT_DIR/all-lstmf" > "$OUTPUT_DIR/list.eval"
[ -s "$OUTPUT_DIR/list.eval" ] || cp "$OUTPUT_DIR/list.train" "$OUTPUT_DIR/list.eval"
echo "   train=$(wc -l < "$OUTPUT_DIR/list.train") eval=$(wc -l < "$OUTPUT_DIR/list.eval")"

# Mirror CI's disk reclaim: drop the large image/box files once lstmf exist.
# Keep *.gt.txt — Phase 2a reads them to extend the unicharset.
find "$GT_DIR" -maxdepth 1 \( -name '*.png' -o -name '*.tif' -o -name '*.tiff' -o -name '*.box' \) -delete 2>/dev/null || true

echo "-- phase 2a: extend unicharset (stock + glyphs from GT)"
# NORM_MODE/RECODER: Latin defaults. RTL scripts (ara/heb) need NORM_MODE=3 + --lang_is_rtl.
NORM_MODE="${NORM_MODE:-2}"
RECODER="${RECODER:---pass_through_recoder}"
combine_tessdata -u "$TESSDATA/$MODEL.traineddata" "$OUTPUT_DIR/$MODEL." >/dev/null 2>&1
[ -s "$OUTPUT_DIR/$MODEL.lstm-unicharset" ] || { echo "ERROR: no stock unicharset extracted"; exit 1; }
find "$GT_DIR" -maxdepth 1 -name '*.gt.txt' -exec cat {} + > "$OUTPUT_DIR/all-gt"
unicharset_extractor --output_unicharset "$OUTPUT_DIR/my.unicharset" \
  --norm_mode "$NORM_MODE" "$OUTPUT_DIR/all-gt"
merge_unicharsets "$OUTPUT_DIR/$MODEL.lstm-unicharset" "$OUTPUT_DIR/my.unicharset" \
  "$OUTPUT_DIR/unicharset"
STOCK_CHARS=$(head -1 "$OUTPUT_DIR/$MODEL.lstm-unicharset")
MERGED_CHARS=$(head -1 "$OUTPUT_DIR/unicharset")
echo "   unicharset: stock=$STOCK_CHARS -> merged=$MERGED_CHARS (+$((MERGED_CHARS - STOCK_CHARS)) glyphs)"

echo "-- phase 2b: build proto model with extended unicharset"
combine_lang_model \
  --input_unicharset "$OUTPUT_DIR/unicharset" \
  --script_dir "$LANGDATA_DIR" \
  --numbers "$OUTPUT_DIR/$MODEL.numbers" \
  --puncs "$OUTPUT_DIR/$MODEL.punc" \
  --words "$OUTPUT_DIR/$MODEL.wordlist" \
  --output_dir "$WORK/data" \
  $RECODER \
  --lang "$MODEL"
PROTO="$WORK/data/$MODEL/$MODEL.traineddata"
[ -s "$PROTO" ] || { echo "ERROR: combine_lang_model produced no proto model"; exit 1; }

echo "-- phase 2c: fine-tune with char-set expansion (--old_traineddata, LR 0.00001)"
combine_tessdata -e "$TESSDATA/$MODEL.traineddata" "$OUTPUT_DIR/$MODEL.lstm"
[ -s "$OUTPUT_DIR/$MODEL.lstm" ] || { echo "ERROR: failed to extract stock LSTM"; exit 1; }
set +e
lstmtraining \
  --traineddata "$PROTO" \
  --old_traineddata "$TESSDATA/$MODEL.traineddata" \
  --continue_from "$OUTPUT_DIR/$MODEL.lstm" \
  --learning_rate 0.00001 \
  --model_output "$OUTPUT_DIR/checkpoints/$MODEL" \
  --train_listfile "$OUTPUT_DIR/list.train" \
  --eval_listfile "$OUTPUT_DIR/list.eval" \
  --max_iterations "$MAX_ITERATIONS" \
  --target_error_rate 0.005 \
  --debug_interval 0
rc=$?
set -e
CKPT=$(ls -t "$OUTPUT_DIR"/checkpoints/${MODEL}*checkpoint 2>/dev/null | head -1)
[ -n "$CKPT" ] || { echo "ERROR: no checkpoint (rc=$rc)"; exit 1; }

echo "-- phase 3: package"
lstmtraining --stop_training --continue_from "$CKPT" \
  --traineddata "$PROTO" \
  --model_output "$OUT_REPO/$LANG_CODE.traineddata"
echo "OK -> training/local/out/$LANG_CODE.traineddata ($(wc -c < "$OUT_REPO/$LANG_CODE.traineddata") bytes)"

if [ -f "$REPO/training/held-out/$LANG_CODE.txt" ]; then
  echo "-- benchmark vs held-out"
  python3 "$REPO/training/scripts/benchmark.py" --lang "$LANG_CODE" \
    --tessdata "$OUT_REPO" --held-out "$REPO/training/held-out/$LANG_CODE.txt" \
    --render-dir "/tmp/bench_$LANG_CODE" --model-tag current \
    --output "/tmp/bench_$LANG_CODE.json" --max-lines 50 || true
fi
