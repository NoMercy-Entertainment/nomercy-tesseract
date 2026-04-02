# nomercy-tesseract

Fine-tuned Tesseract 5 LSTM models for NoMercy MediaServer.

The server downloads `.traineddata` files from `tessdata/` in this repository to
perform OCR on DVD and Blu-ray bitmap subtitle tracks (PGS / VOBSUB).

## Why fine-tune?

The stock `eng.traineddata` from `tesseract-ocr/tessdata` was never trained on
common subtitle characters such as music note symbols.  As a result the OCR
engine misreads them:

| Actual character | Common OCR output |
|-----------------|------------------|
| ♪               | &, J, I, or '    |
| ♫               | I, F, or J       |
| …               | ...              |
| –               | -                |

The models in `tessdata/` are fine-tuned to fix these specific issues while
leaving the base language recognition intact.

## Repository layout

```
tessdata/           Fine-tuned .traineddata files (downloaded by NoMercy server)
training/
  ground-truth/     Manually verified image+text pairs used for training and validation
  fonts/            Where to place extra .ttf fonts (see fonts/README.md)
  scripts/
    generate-training-data.py   Renders synthetic subtitle training images
    validate-model.py           Tests models against ground-truth before committing
  config/
    characters.txt  Extra characters to cover in training
    languages.txt   Language codes to fine-tune
.github/
  workflows/
    train.yml       CI/CD pipeline — triggers on changes to training/
```

## How the CI pipeline works

1. Push a change to any file under `training/` (or trigger manually via Actions tab).
2. GitHub Actions resolves the language list from `training/config/languages.txt`.
3. For each language in parallel:
   a. Installs Tesseract 5 training tools via apt.
   b. Downloads the base LSTM model from the installed package.
   c. Runs `generate-training-data.py` to produce synthetic subtitle images
      (white/yellow text on black background, multiple fonts and sizes).
   d. Appends the manual ground-truth pairs from `training/ground-truth/`.
   e. Converts all images to `.lstmf` format.
   f. Runs `lstmtraining --continue_from` to fine-tune (NOT from scratch).
   g. Packages the result back into a `.traineddata` file.
   h. Runs `validate-model.py` — the model must read every ground-truth image
      with 100% character accuracy.
   i. If validation passes, commits the updated `.traineddata` to `tessdata/`.

## Adding a correction

If you find a subtitle that OCR reads incorrectly:

1. Crop the subtitle bitmap to the affected line (PNG, black background, white text).
2. Name it `{lang}_{category}_{seq:03d}.png` (e.g. `eng_music_006.png`).
3. Create a matching `.gt.txt` file with the exact correct text (UTF-8).
4. Place both files in `training/ground-truth/`.
5. Push to `master` — the pipeline will retrain automatically.

## Running locally

```bash
# Install Python dependencies
pip install Pillow

# Generate training images for English only
python training/scripts/generate-training-data.py --lang eng

# Validate an existing tessdata directory
python training/scripts/validate-model.py --tessdata tessdata/ --lang eng

# Preview sample renders without writing files
python training/scripts/generate-training-data.py --preview
```

Tesseract 5 training tools must be on PATH for the validate script:
```bash
sudo apt-get install tesseract-ocr libtesseract-dev tesseract-ocr-all
```

## Triggering a manual rebuild

Go to **Actions → Fine-tune Tesseract models → Run workflow**.
Optionally specify:
- **languages** — comma-separated codes (e.g. `eng,fra`). Leave blank for all.
- **max_iterations** — default is 400. Increase if accuracy is still low.

## Iteration count guidance

| Situation | Recommended iterations |
|-----------|----------------------|
| Adding a handful of new characters | 300–400 |
| Fixing accented character set for a new language | 400–600 |
| Large new ground-truth dataset (100+ pairs) | 600–1000 |

Keep iterations low. These models fine-tune a large pre-trained base — a small
number of extra iterations is enough to teach new characters without forgetting
the rest of the language.
