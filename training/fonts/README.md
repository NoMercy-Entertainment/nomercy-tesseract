# Subtitle Fonts

The training pipeline renders synthetic subtitle images using freely available fonts.
The `generate-training-data.py` script will download these automatically on a CI runner,
but if you are running locally you can place `.ttf` files directly in this directory.

## Fonts used in training

| Font | Why chosen | Source |
|------|-----------|--------|
| Liberation Sans | Near pixel-perfect Arial replacement; default on most Linux subtitle tracks | `fonts-liberation` apt package |
| DejaVu Sans | Excellent Unicode coverage; includes ♪ ♫ and accented chars | `fonts-dejavu` apt package |
| Noto Sans | Google's pan-Unicode fallback; covers every character in characters.txt | `fonts-noto` apt package |
| FreeSans | GNU freefont; common on older DVD subtitle renders | `fonts-freefont-ttf` apt package |

## DVD / Blu-ray subtitle rendering characteristics

The training data should mimic what Tesseract actually sees after bitmap subtitle extraction.
Key properties to replicate:

- **Background:** pure black (0, 0, 0) or transparent — keep it black for training
- **Text colour:** white (255, 255, 255) for dialogue; yellow (255, 255, 0) for karaoke/songs
- **Font size:** 28–42 px for 720x480 (SD/DVD); 52–72 px for 1920x1080 (Blu-ray)
- **Anti-aliasing:** slight (Lanczos or bilinear) — do NOT use sharp/no AA
- **Outline:** 1–2 px black outline is normal; the generator adds this by default
- **Aspect ratio:** images are cropped to the text bounding box + 8 px padding each side

## Adding a new font

1. Place the `.ttf` file here.
2. Add its path to the `FONTS` list in `scripts/generate-training-data.py`.
3. Run the generator locally to verify it renders the characters you need:
   ```
   python training/scripts/generate-training-data.py --preview
   ```

## Important: do NOT commit proprietary fonts

Arial, Times New Roman, Calibri etc. are proprietary. Use only fonts with OFL or GPL licences.
