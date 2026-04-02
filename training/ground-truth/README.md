# Ground-Truth Training Data

This directory contains manually verified image/text pairs used for fine-tuning.
Each pair consists of:

- `<name>.png` — the raw subtitle bitmap as Tesseract would receive it
- `<name>.gt.txt` — the exact correct text the image contains (UTF-8, no trailing newline)

These are the GOLD standard corrections. They are used in two ways:
1. As additional training samples fed directly into `lstmtraining`
2. As the validation set in `validate-model.py` — the fine-tuned model must read every
   image here 100% correctly before its `.traineddata` is committed to `tessdata/`

## Naming convention

```
{language}_{category}_{seq:03d}
```

Examples:
- `eng_music_001.png` / `eng_music_001.gt.txt`
- `eng_music_002.png` / `eng_music_002.gt.txt`
- `fra_accents_001.png` / `fra_accents_001.gt.txt`

## How to add a correction

1. Find a subtitle frame where Tesseract gives the wrong output.
2. Crop the subtitle bitmap to just the line that is wrong (or the whole subtitle region).
3. Save it as a PNG in this directory using the naming convention above.
4. Create the matching `.gt.txt` with the exact correct text.
5. Open a PR or push directly to `master` — the `train.yml` workflow will pick it up.

## Current ground-truth entries

| File | Correct text | Known bad OCR output |
|------|-------------|----------------------|
| eng_music_001 | ♪ Never gonna give you up ♪ | & Never gonna give you up & |
| eng_music_002 | ♪ La la la ♪ | J La la la J |
| eng_music_003 | ♫ Singing in the rain ♫ | I Singing in the rain I |
| eng_music_004 | ♪ | ' |
| eng_ellipsis_001 | I don't know… | I don't know... (acceptable but training on proper char) |

## Minimum validation threshold

The CI workflow requires 100% character accuracy on all ground-truth pairs.
If the fine-tuned model fails on any entry, the workflow fails and the old
`tessdata/` files are NOT overwritten.
