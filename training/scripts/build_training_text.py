#!/usr/bin/env python3
"""
build_training_text.py
======================
Generates .training_text and .fonts files that tesstrain/text2image can
consume directly. Replaces the Pillow-based image generation approach.

Usage:
    python3 training/scripts/build_training_text.py --lang eng
    python3 training/scripts/build_training_text.py --lang eng --output out.txt
    python3 training/scripts/build_training_text.py --all --output-dir training/generated/
"""

import argparse
import random
import sys
from pathlib import Path
from typing import Dict, List, Set


# ── Language-to-character-group mapping ──────────────────────────────────────

LANG_GROUPS: Dict[str, List[str]] = {
    # ── Western European ────────────────────────────────────────
    "eng": ["latin_western"],
    "enm": ["latin_western"],
    "spa": ["latin_western"],
    "spa_old": ["latin_western"],
    "fra": ["latin_western"],
    "frm": ["latin_western"],
    "deu": ["latin_western"],
    "deu_frak": ["latin_western"],
    "deu_latf": ["latin_western"],
    "ger": ["latin_western"],
    "ita": ["latin_western"],
    "ita_old": ["latin_western"],
    "por": ["latin_western"],
    "nld": ["latin_western"],
    "dut": ["latin_western"],
    "cat": ["latin_western"],
    "glg": ["latin_western"],
    "eus": ["latin_western"],
    "oci": ["latin_western"],
    "cos": ["latin_western"],
    "hat": ["latin_western"],
    "epo": ["latin_western"],
    "lat": ["latin_western"],
    "fry": ["latin_western"],
    "ltz": ["latin_western"],
    "bre": ["latin_western"],
    "gla": ["latin_western"],
    # ── Nordic ──────────────────────────────────────────────────
    "swe": ["latin_western", "latin_nordic"],
    "nor": ["latin_western", "latin_nordic"],
    "dan": ["latin_western", "latin_nordic"],
    "dan_frak": ["latin_western", "latin_nordic"],
    "fin": ["latin_western", "latin_nordic"],
    "isl": ["latin_western", "latin_nordic"],
    "fao": ["latin_western", "latin_nordic"],
    # ── Central/Eastern European ────────────────────────────────
    "pol": ["latin_western", "latin_polish"],
    "ces": ["latin_western", "latin_czech_slovak"],
    "slk": ["latin_western", "latin_czech_slovak"],
    "slk_frak": ["latin_western", "latin_czech_slovak"],
    "hun": ["latin_western", "latin_hungarian"],
    "ron": ["latin_western", "latin_romanian"],
    "hrv": ["latin_western", "latin_croatian_serbian_latin"],
    "srp_latn": ["latin_western", "latin_croatian_serbian_latin"],
    "slv": ["latin_western", "latin_croatian_serbian_latin"],
    "bos": ["latin_western", "latin_croatian_serbian_latin"],
    "sqi": ["latin_western", "latin_albanian"],
    "est": ["latin_western", "latin_estonian"],
    "lav": ["latin_western", "latin_latvian_lithuanian"],
    "lit": ["latin_western", "latin_latvian_lithuanian"],
    # ── Turkic ──────────────────────────────────────────────────
    "tur": ["latin_western", "latin_turkish"],
    "aze": ["latin_western", "latin_turkish"],
    "aze_cyrl": ["cyrillic"],
    "tat": ["cyrillic"],
    "uzb": ["latin_western"],
    "uzb_cyrl": ["cyrillic"],
    "kir": ["cyrillic"],
    "tgk": ["cyrillic"],
    "uig": ["arabic"],
    # ── Cyrillic ────────────────────────────────────────────────
    "rus": ["cyrillic"],
    "ukr": ["cyrillic"],
    "bul": ["cyrillic"],
    "mkd": ["cyrillic"],
    "bel": ["cyrillic"],
    "srp": ["cyrillic"],
    "kaz": ["cyrillic"],
    "mon": ["cyrillic"],
    # ── Greek ───────────────────────────────────────────────────
    "ell": ["greek"],
    "grc": ["greek"],
    # ── CJK ─────────────────────────────────────────────────────
    "jpn": ["japanese"],
    "jpn_vert": ["japanese"],
    "kor": ["korean"],
    "kor_vert": ["korean"],
    "chi_sim": ["chinese"],
    "chi_sim_vert": ["chinese"],
    "chi_tra": ["chinese"],
    "chi_tra_vert": ["chinese"],
    # ── Arabic script ───────────────────────────────────────────
    "ara": ["arabic"],
    "fas": ["arabic"],
    "urd": ["arabic"],
    "pus": ["arabic"],
    "snd": ["arabic"],
    "div": ["arabic"],
    "syr": ["arabic"],
    "kmr": ["latin_western"],
    # ── Hebrew ──────────────────────────────────────────────────
    "heb": ["hebrew"],
    "yid": ["hebrew"],
    # ── Indic ───────────────────────────────────────────────────
    "hin": ["hindi"],
    "mar": ["hindi"],
    "nep": ["hindi"],
    "san": ["hindi"],
    "ori": ["hindi"],
    "bod": ["hindi"],
    "ben": ["bengali"],
    "asm": ["bengali"],
    "tam": ["tamil"],
    "tel": ["telugu"],
    "kan": ["kannada"],
    "mal": ["malayalam"],
    "guj": ["gujarati"],
    "pan": ["punjabi"],
    # ── Southeast Asian ─────────────────────────────────────────
    "tha": ["thai"],
    "khm": ["khmer"],
    "lao": ["lao"],
    "mya": ["burmese"],
    "vie": ["latin_western", "latin_vietnamese"],
    "ind": [],
    "msa": [],
    "tgl": ["latin_tagalog"],
    "fil": ["latin_tagalog"],
    "ceb": [],
    "jav": [],
    "sun": [],
    # ── Other scripts ───────────────────────────────────────────
    "kat": ["georgian"],
    "kat_old": ["georgian"],
    "hye": ["armenian"],
    "amh": ["ethiopic"],
    "tir": ["ethiopic"],
    "sin": ["sinhala"],
    "chr": [],
    "iku": [],
    "dzo": [],
    "ton": [],
    "que": ["latin_western"],
    "mri": [],
    "yor": [],
    # ── Celtic ──────────────────────────────────────────────────
    "cym": ["latin_western", "latin_welsh"],
    "gle": ["latin_western", "latin_irish"],
    # ── African ─────────────────────────────────────────────────
    "swa": [],
    "afr": ["latin_western"],
    # ── Maltese ─────────────────────────────────────────────────
    "mlt": ["latin_western", "latin_maltese"],
    # ── Special ─────────────────────────────────────────────────
    "equ": [],
    "osd": [],
}


# ── Script-family to Noto font mapping ───────────────────────────────────────

# Maps a set of LANG_GROUPS group names to font lists. Languages are matched
# by inspecting which groups they use; the first matching rule wins.
_SCRIPT_FONT_MAP: List[tuple] = [
    # (frozenset of group name patterns, font list)
    ({"japanese"},          ["Noto Sans CJK JP"]),
    ({"korean"},            ["Noto Sans CJK KR"]),
    # chi_sim and chi_tra share the "chinese" group — differentiate by lang
    # at call time; the function below handles that special case.
    ({"chinese"},           ["Noto Sans CJK SC"]),
    ({"arabic"},            ["Noto Naskh Arabic", "Noto Sans Arabic"]),
    ({"hebrew"},            ["Noto Sans Hebrew"]),
    ({"hindi"},             ["Noto Sans Devanagari"]),
    ({"bengali"},           ["Noto Sans Bengali"]),
    ({"thai"},              ["Noto Sans Thai"]),
    ({"tamil"},             ["Noto Sans Tamil"]),
    ({"telugu"},            ["Noto Sans Telugu"]),
    ({"kannada"},           ["Noto Sans Kannada"]),
    ({"malayalam"},         ["Noto Sans Malayalam"]),
    ({"gujarati"},          ["Noto Sans Gujarati"]),
    ({"punjabi"},           ["Noto Sans Gurmukhi"]),
    ({"georgian"},          ["Noto Sans Georgian"]),
    ({"armenian"},          ["Noto Sans Armenian"]),
    ({"ethiopic"},          ["Noto Sans Ethiopic"]),
    ({"sinhala"},           ["Noto Sans Sinhala"]),
    ({"khmer"},             ["Noto Sans Khmer"]),
    ({"lao"},               ["Noto Sans Lao"]),
    ({"burmese"},           ["Noto Sans Myanmar"]),
    ({"greek"},             ["Noto Sans", "Noto Serif", "DejaVu Sans"]),
    ({"cyrillic"},          ["Noto Sans", "Noto Serif", "DejaVu Sans"]),
    # Latin (any variant) falls through to the default below
]

_LATIN_FONTS = ["Noto Sans", "Noto Serif", "DejaVu Sans"]


def get_fonts_for_lang(lang: str) -> List[str]:
    """Return a list of font names suitable for the given language's script."""
    groups = set(LANG_GROUPS.get(lang, []))

    # Chinese Traditional needs a different font than Simplified
    if lang in ("chi_tra", "chi_tra_vert"):
        return ["Noto Sans CJK TC"]

    for script_groups, fonts in _SCRIPT_FONT_MAP:
        if groups & script_groups:
            return fonts

    # Latin-based scripts (all latin_* groups) or empty group list
    return _LATIN_FONTS


# ── Core helpers (copied from generate_training_data.py) ─────────────────────

def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def parse_characters(path: Path) -> Dict[str, List[str]]:
    """Parse grouped characters.txt into {group_name: [characters]}."""
    groups: Dict[str, List[str]] = {}
    current_group = "universal"
    groups[current_group] = []

    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            current_group = stripped[1:-1]
            groups.setdefault(current_group, [])
            continue
        for token in stripped.split():
            groups[current_group].append(token)

    return groups


def get_chars_for_lang(lang: str, groups: Dict[str, List[str]]) -> List[str]:
    """Get characters relevant to a specific language."""
    chars: List[str] = list(groups.get("universal", []))
    lang_groups = LANG_GROUPS.get(lang, [])
    for group_name in lang_groups:
        chars.extend(groups.get(group_name, []))
    # Deduplicate preserving order
    seen: Set[str] = set()
    unique: List[str] = []
    for c in chars:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique


def get_languages_from_tessdata(tessdata_dir: Path) -> List[str]:
    """Discover all languages from .traineddata files in tessdata/."""
    return sorted(
        p.stem for p in tessdata_dir.glob("*.traineddata")
        if p.stem not in ("osd", "equ")  # skip non-language models
    )


# ── Localized subtitle sentences per language ────────────────────────────────
#
# Real sentences that exercise each language's special characters naturally.
# These are what Tesseract will actually encounter in subtitle OCR.
# Sentences are written to hit diacritics, special punctuation, and common
# character combinations for each script.
#
# Languages sharing the same base (e.g. deu/ger, nld/dut, spa/spa_old)
# are aliased at the end.

LANG_SENTENCES: Dict[str, List[str]] = {
    "eng": [
        # Dialogue
        "I don't know what you're talking about.",
        "She looked at him and smiled.",
        "They never found out the truth.",
        "Hello? Is anyone there?",
        "I said I was sorry!",
        "Previously on...",
        "To be continued.",
        "- Yes.  - No.",
        'He said: "I\'ll be back."',
        '"Wait for me!" she cried.',
        "...I don't know.",
        "What? Why?",
        "- Are you sure about this?",
        "- Absolutely.",
        "How much time do we have?",
        "It was 3:47 in the morning.",
        "This can't be happening.",
        "I've seen this before.",
        "Open the door!",
        "Stay back!",
        "Help me!",
        "I love you too.",
        "Goodbye.",
        "Thank you for everything.",
        "You were right all along.",
        "We made it.",
        "It's over.",
        "We need to talk about what happened last night.",
        "I can't believe you just said that to me.",
        "How much time do we have left before they arrive?",
        "She said she would come back, but she never did.",
        "They were supposed to be here an hour ago.",
        "Something doesn't feel right about this place.",
        "I thought we agreed not to talk about this.",
        "Do you remember what happened yesterday afternoon?",
        "The police are on their way, just stay calm.",
        "Everything is going to be okay, I promise you.",
        # SDH (Subtitles for Deaf/Hard of Hearing)
        "[ Door creaks loudly in the background ]",
        "[ Suspenseful music playing softly ]",
        "[ Thunder rumbling in the distance ]",
        "[ Footsteps approaching from behind ]",
        "[ Glass shattering on the floor ]",
        "[ Phone ringing in the other room ]",
        "[ Birds chirping in the morning ]",
        "[ Engine revving loudly outside ]",
        "[ Crowd cheering in the stadium ]",
        "[ Wind howling through the trees ]",
        "( sighs deeply and looks away )",
        "( laughs nervously at the joke )",
        "( gasps in shock and disbelief )",
        "( whispers ) Can you hear me now?",
        "( sobbing ) I can't do this anymore.",
        "( clears throat ) As I was saying...",
        "( speaking in foreign language )",
        "( inaudible ) ...something happened.",
        "- Are you absolutely sure about this?",
        "- I've never been more sure in my life.",
        "- What do you mean by that exactly?",
        "- It's complicated. I'll explain later.",
        # Music note lines — heavily represented for ♪ training
        "\u266a Never gonna give you up \u266a",
        "\u266a Never gonna let you down \u266a",
        "\u266a Never gonna run around and desert you \u266a",
        "\u266a La la la la la la la la \u266a",
        "\u266a Singing in the rain, just singing in the rain \u266a",
        "\u266a Don't stop believin', hold on to that feeling \u266a",
        "\u266a Somewhere over the rainbow, way up high \u266a",
        "\u266a Happy birthday to you, happy birthday \u266a",
        "\u266a We are the champions, my friends \u266a",
        "\u266a Twinkle twinkle little star, how I wonder \u266a",
        "\u266a Jingle bells, jingle bells, jingle all the way \u266a",
        "\u266a Yesterday, all my troubles seemed so far away \u266a",
        "\u266a Let it be, let it be, let it be, let it be \u266a",
        "\u266a Row row row your boat, gently down the stream \u266a",
        "\u266a Amazing grace, how sweet the sound \u266a",
        "\u266a You are my sunshine, my only sunshine \u266a",
        "\u266a When the saints go marching in \u266a",
        "\u266a Take me out to the ball game, take me out \u266a",
        "\u266a This land is your land, this land is my land \u266a",
        "\u266a I will always love you, and I \u266a",
        "\u266a Bohemian Rhapsody, is this the real life \u266a",
        "\u266a Hey Jude, don't make it bad, take a sad song \u266a",
        "\u266a Imagine all the people, living for today \u266a",
        "\u266a What a wonderful world, I see trees of green \u266a",
        "\u266a Like a rolling stone, how does it feel \u266a",
        "\u266a Bridge over troubled water, I will lay me down \u266a",
        "\u266a Hotel California, such a lovely place \u266a",
        "\u266a We will, we will rock you, rock you \u266a",
        "\u266a Another one bites the dust, and another one \u266a",
        "\u266a Under pressure, pushing down on me \u266a",
        "\u266a Sweet child o' mine, she's got a smile \u266a",
        "\u266a Smells like teen spirit, with the lights out \u266a",
        "\u266a Come as you are, as you were, as I want you \u266a",
        "\u266a Billie Jean is not my lover, she's just a girl \u266a",
        "\u266b Singing in the rain, just singing in the rain \u266b",
        "\u266b What a glorious feeling, I'm happy again \u266b",
        "\u266b Do re mi fa sol la ti do, do ti la sol \u266b",
        "\u266a Stairway to heaven, and she's buying \u266a",
    ],
    "fra": [
        "Je ne sais pas ce que tu veux dire.",
        "Qu'est-ce qui s'est pass\u00e9 hier soir ?",
        "Elle l'a regard\u00e9 et a souri.",
        "O\u00f9 \u00e9tiez-vous pass\u00e9 ?",
        "C'est impossible !",
        "- Vous \u00eates s\u00fbr ?  - Absolument.",
        "Il a dit : \u00ab Je reviendrai. \u00bb",
        "Au revoir.",
        "Merci pour tout.",
        "Je t'aime aussi.",
        "\u00c0 bient\u00f4t.",
        "Arr\u00eatez ! Ne bougez plus !",
        "Pr\u00e9c\u00e9demment...",
        "\u00c7a ne peut pas \u00eatre vrai.",
        "[ Porte qui grince ]",
        "( soupire )",
        "D\u00e9p\u00eachez-vous !",
        "No\u00ebl approche, les enfants sont excit\u00e9s.",
        "Fran\u00e7ois a re\u00e7u une le\u00e7on.",
        "L'\u0153uvre d'art co\u00fbte tr\u00e8s cher.",
        "\u266a Fr\u00e8re Jacques, dormez-vous ? \u266a",
    ],
    "deu": [
        "Ich wei\u00df nicht, wovon du redest.",
        "Was ist gestern Nacht passiert?",
        "\u00d6ffne die T\u00fcr!",
        "Das kann nicht wahr sein.",
        "Entschuldigung, k\u00f6nnen Sie das wiederholen?",
        "- Bist du sicher?  - Nat\u00fcrlich.",
        "Er hat gesagt: \u201eIch komme zur\u00fcck.\u201c",
        "Danke f\u00fcr alles.",
        "Tsch\u00fc\u00df.",
        "Ich liebe dich auch.",
        "Wir haben es geschafft.",
        "Es ist vorbei.",
        "Fr\u00fcher, in einer fr\u00fcheren Folge...",
        "[ T\u00fcr knarrt ]",
        "( seufzt )",
        "Gr\u00f6\u00dfe ist nicht alles.",
        "Die Stra\u00dfe f\u00fchrt \u00fcber den Flu\u00df.",
        "\u00c4rzte empfehlen mehr Gem\u00fcse.",
        "Das M\u00e4dchen tr\u00e4gt einen h\u00fcbschen Schl\u00fcssel.",
        "\u266a Stille Nacht, heilige Nacht \u266a",
    ],
    "spa": [
        "No s\u00e9 de qu\u00e9 est\u00e1s hablando.",
        "\u00bfQu\u00e9 pas\u00f3 anoche?",
        "\u00a1Abre la puerta!",
        "Eso no puede ser verdad.",
        "- \u00bfEst\u00e1s seguro?  - Por supuesto.",
        "\u00c9l dijo: \u00abVolver\u00e9.\u00bb",
        "Adi\u00f3s.",
        "Gracias por todo.",
        "Yo tambi\u00e9n te quiero.",
        "Lo logramos.",
        "Se acab\u00f3.",
        "[ Puerta cruje ]",
        "( suspira )",
        "\u00a1D\u00e9jame en paz!",
        "\u00bfCu\u00e1nto tiempo tenemos?",
        "Ma\u00f1ana ser\u00e1 un d\u00eda mejor.",
        "El ni\u00f1o jug\u00f3 en el jard\u00edn.",
        "La se\u00f1ora habl\u00f3 con pasi\u00f3n.",
        "\u266a Cielito lindo, ay ay ay ay \u266a",
    ],
    "ita": [
        "Non so di cosa stai parlando.",
        "Cos'\u00e8 successo ieri sera?",
        "Apri la porta!",
        "Non pu\u00f2 essere vero.",
        "- Sei sicuro?  - Assolutamente.",
        'Ha detto: "Torner\u00f2."',
        "Arrivederci.",
        "Grazie di tutto.",
        "Ti amo anch'io.",
        "Ce l'abbiamo fatta.",
        "\u00c8 finita.",
        "[ Porta che scricchiola ]",
        "( sospira )",
        "Perch\u00e9 non l'hai detto prima?",
        "La citt\u00e0 \u00e8 pi\u00f9 bella di notte.",
        "Non \u00e8 possibile cos\u00ec.",
        "\u266a O sole mio, sta 'nfronte a te \u266a",
    ],
    "por": [
        "N\u00e3o sei do que voc\u00ea est\u00e1 falando.",
        "O que aconteceu ontem \u00e0 noite?",
        "Abre a porta!",
        "Isso n\u00e3o pode ser verdade.",
        "- Tem certeza?  - Com certeza.",
        "Adeus.",
        "Obrigado por tudo.",
        "Eu tamb\u00e9m te amo.",
        "Conseguimos.",
        "Acabou.",
        "[ Porta range ]",
        "( suspira )",
        "A crian\u00e7a correu pelo jardim.",
        "S\u00e3o Paulo \u00e9 uma cidade enorme.",
        "Ele n\u00e3o sabe o que fa\u00e7o aqu\u00ed.",
        "A a\u00e7\u00e3o come\u00e7ou \u00e0s tr\u00eas horas.",
        "\u266a Garota de Ipanema \u266a",
    ],
    "nld": [
        "Ik weet niet waar je het over hebt.",
        "Wat is er gisteravond gebeurd?",
        "Doe de deur open!",
        "Dat kan niet waar zijn.",
        "- Weet je het zeker?  - Absoluut.",
        "Tot ziens.",
        "Bedankt voor alles.",
        "Ik hou ook van jou.",
        "We hebben het gehaald.",
        "Het is voorbij.",
        "[ Deur kraakt ]",
        "( zucht )",
        "Waar gaan we naartoe?",
        "Hij kan het niet geloven.",
        "De grachten zijn bevroren.",
        "Ze heeft de brief ge\u00ebllustreerd.",
        "E\u00e9n kopje koffie alstublieft.",
        "\u266a Lang zal ze leven \u266a",
    ],
    "swe": [
        "Jag vet inte vad du pratar om.",
        "Vad h\u00e4nde ig\u00e5r kv\u00e4ll?",
        "\u00d6ppna d\u00f6rren!",
        "Det kan inte vara sant.",
        "- \u00c4r du s\u00e4ker?  - Absolut.",
        "Hej d\u00e5.",
        "Tack f\u00f6r allt.",
        "Jag \u00e4lskar dig ocks\u00e5.",
        "Vi klarade det.",
        "Det \u00e4r \u00f6ver.",
        "[ D\u00f6rr knarrar ]",
        "( suckar )",
        "Var \u00e4r du n\u00e5gonstans?",
        "F\u00f6rl\u00e5t, kan du s\u00e4ga det igen?",
        "G\u00f6teborg \u00e4r en v\u00e4ldigt fin stad.",
        "H\u00f6sten \u00e4r h\u00e4r och l\u00f6ven faller.",
        "\u00c5rets f\u00f6rsta sn\u00f6 har kommit.",
        "Sk\u00e5l! L\u00e5t oss fira!",
        "\u266a Du gamla, du fria \u266a",
    ],
    "nor": [
        "Jeg vet ikke hva du snakker om.",
        "Hva skjedde i g\u00e5r kveld?",
        "\u00c5pne d\u00f8ren!",
        "Det kan ikke v\u00e6re sant.",
        "- Er du sikker?  - Absolutt.",
        "Ha det bra.",
        "Takk for alt.",
        "Jeg elsker deg ogs\u00e5.",
        "Vi klarte det.",
        "Det er over.",
        "[ D\u00f8r knirker ]",
        "( sukker )",
        "Hvor er du hen?",
        "Unnskyld, kan du si det igjen?",
        "Bl\u00e5b\u00e6r vokser i de norske fjellene.",
        "\u00d8yvind g\u00e5r p\u00e5 sk\u00f8yter n\u00e5.",
        "V\u00e6ret er fint i Troms\u00f8.",
        "\u266a Ja, vi elsker dette landet \u266a",
    ],
    "dan": [
        "Jeg ved ikke, hvad du taler om.",
        "Hvad skete der i g\u00e5r aftes?",
        "\u00c5bn d\u00f8ren!",
        "Det kan ikke v\u00e6re sandt.",
        "- Er du sikker?  - Helt sikkert.",
        "Farvel.",
        "Tak for alt.",
        "Jeg elsker dig ogs\u00e5.",
        "Vi klarede det.",
        "Det er forbi.",
        "[ D\u00f8r knirker ]",
        "( sukker )",
        "Hvor er du henne?",
        "K\u00f8benhavn er en smuk by.",
        "R\u00f8dgr\u00f8d med fl\u00f8de, tak.",
        "B\u00f8rnene leger i g\u00e5rden.",
        "\u266a Der er et yndigt land \u266a",
    ],
    "fin": [
        "En tied\u00e4 mist\u00e4 puhut.",
        "Mit\u00e4 eilen illalla tapahtui?",
        "Avaa ovi!",
        "Se ei voi olla totta.",
        "- Oletko varma?  - Ehdottomasti.",
        "N\u00e4kemiin.",
        "Kiitos kaikesta.",
        "Min\u00e4kin rakastan sinua.",
        "Me selvittiin.",
        "Se on ohi.",
        "[ Ovi narisee ]",
        "( huokaa )",
        "Miss\u00e4 sin\u00e4 olet?",
        "T\u00e4m\u00e4 on mahdotonta.",
        "Kes\u00e4 Suomessa on kaunis.",
        "H\u00e4n k\u00e4vi l\u00e4\u00e4k\u00e4riss\u00e4 t\u00e4n\u00e4\u00e4n.",
        "Yst\u00e4v\u00e4ni asuu Hels\u00edngiss\u00e4.",
        "\u266a Finlandia, Finlandia \u266a",
    ],
    "pol": [
        "Nie wiem, o czym m\u00f3wisz.",
        "Co si\u0119 sta\u0142o wczoraj w nocy?",
        "Otw\u00f3rz drzwi!",
        "To nie mo\u017ce by\u0107 prawd\u0105.",
        "- Jeste\u015b pewien?  - Oczywi\u015bcie.",
        "Do widzenia.",
        "Dzi\u0119kuj\u0119 za wszystko.",
        "Ja te\u017c ci\u0119 kocham.",
        "Udali\u015bmy si\u0119.",
        "To ju\u017c koniec.",
        "[ Drzwi skrzypi\u0105 ]",
        "( wzdycha )",
        "Gdzie jeste\u015b?",
        "Przepraszam, mo\u017cesz powt\u00f3rzy\u0107?",
        "\u0141\u00f3d\u017a to pi\u0119kne miasto.",
        "Wzi\u0105\u0142 ksi\u0105\u017ck\u0119 z p\u00f3\u0142ki.",
        "\u0179r\u00f3d\u0142o wody jest w g\u00f3rach.",
        "\u017bycie jest skomplikowane.",
        "\u266a Sto lat, sto lat \u266a",
    ],
    "ces": [
        "Nev\u00edm, o \u010dem mluv\u00ed\u0161.",
        "Co se v\u010dera v noci stalo?",
        "Otev\u0159i dve\u0159e!",
        "To nem\u016f\u017ee b\u00fdt pravda.",
        "- Jsi si jist\u00fd?  - Samoz\u0159ejm\u011b.",
        "Na shledanou.",
        "D\u011bkuji za v\u0161echno.",
        "Taky t\u011b miluju.",
        "Zvl\u00e1dli jsme to.",
        "Je konec.",
        "[ Dve\u0159e vr\u017eou ]",
        "( vzd\u00e1l\u00ed se )",
        "Kde jsi?",
        "Promi\u0148, m\u016f\u017ee\u0161 to zopakovat?",
        "Praha je kr\u00e1sn\u00e9 m\u011bsto.",
        "P\u0159\u00ed\u0161t\u011b p\u016fjdeme do kina.",
        "\u0158\u00ed\u010dn\u00ed proud te\u010de rychle.",
        "\u010ce\u0161tina m\u00e1 h\u00e1\u010dky a \u010d\u00e1rky.",
        "\u266a Kde domov m\u016fj \u266a",
    ],
    "slk": [
        "Neviem, o \u010dom hovor\u00ed\u0161.",
        "\u010co sa v\u010dera v noci stalo?",
        "Otvor dvere!",
        "To nem\u00f4\u017ee by\u0165 pravda.",
        "- Si si ist\u00fd?  - Samozrejme.",
        "Dovidenia.",
        "\u010eakujem za v\u0161etko.",
        "Aj ja \u0165a \u013e\u00fabim.",
        "Zvl\u00e1dli sme to.",
        "Je koniec.",
        "Kde si?",
        "Pre\u010do to nepovedal sk\u00f4r?",
        "Bratislava le\u017e\u00ed na Dunaji.",
        "\u013d\u00fadov\u00e9 \u010dakaj\u00fa na n\u00e1mest\u00ed.",
        "\u266a Nad Tatrou sa bl\u00fdska \u266a",
    ],
    "hun": [
        "Nem tudom, mir\u0151l besz\u00e9lsz.",
        "Mi t\u00f6rt\u00e9nt tegnap este?",
        "Nyisd ki az ajt\u00f3t!",
        "Ez nem lehet igaz.",
        "- Biztos vagy benne?  - Term\u00e9szetesen.",
        "Viszontl\u00e1t\u00e1sra.",
        "K\u00f6sz\u00f6n\u00f6m sz\u00e9pen.",
        "\u00c9n is szeretlek.",
        "Siker\u00fclt.",
        "V\u00e9ge.",
        "[ Ajt\u00f3 csikorog ]",
        "( s\u00f3hajt )",
        "Hol vagy?",
        "Eln\u00e9z\u00e9st, megism\u00e9teln\u00e9d?",
        "Budapest gy\u00f6ny\u00f6r\u0171 v\u00e1ros.",
        "Az \u0151sz\u00f6d k\u00f6sz\u00f6nt\u00f6tt.",
        "\u0170z\u00f6tt \u00e1llatokat l\u00e1ttam az erd\u0151ben.",
        "\u266a Tavaszi sz\u00e9l vizet \u00e1raszt \u266a",
    ],
    "ron": [
        "Nu \u0219tiu despre ce vorbe\u0219ti.",
        "Ce s-a \u00eent\u00e2mplat asear\u0103?",
        "Deschide u\u0219a!",
        "Nu poate fi adev\u0103rat.",
        "- E\u0219ti sigur?  - Absolut.",
        "La revedere.",
        "Mul\u021bumesc pentru tot.",
        "\u0218i eu te iubesc.",
        "Am reu\u0219it.",
        "S-a terminat.",
        "[ U\u0219\u0103 sc\u00e2r\u021b\u00e2ie ]",
        "( oft\u00e2nd )",
        "Unde e\u0219ti?",
        "Bucure\u0219ti este capitala Rom\u00e2niei.",
        "Gr\u0103dini\u021ba e plin\u0103 de flori.",
        "\u0162ara Oa\u0219ului este frumoas\u0103.",
        "\u266a Trei culori cunosc pe lume \u266a",
    ],
    "tur": [
        "Ne dedi\u011fini bilmiyorum.",
        "D\u00fcn gece ne oldu?",
        "Kap\u0131y\u0131 a\u00e7!",
        "Bu do\u011fru olamaz.",
        "- Emin misin?  - Kesinlikle.",
        "Ho\u015f\u00e7a kal.",
        "Her \u015fey i\u00e7in te\u015fekk\u00fcrler.",
        "Ben de seni seviyorum.",
        "Ba\u015fard\u0131k.",
        "Bitti.",
        "[ Kap\u0131 g\u0131c\u0131rdar ]",
        "( i\u00e7 \u00e7eker )",
        "Neredesin?",
        "\u0130stanbul \u00e7ok g\u00fczel bir \u015fehir.",
        "\u00c7ocuklar bah\u00e7ede oynuyor.",
        "G\u00f6r\u00fc\u015fmek \u00fczere.",
        "\u00d6\u011fretmen \u00f6\u011frencilere \u00f6dev verdi.",
        "\u266a \u0130zmir'in da\u011flar\u0131nda \u00e7i\u00e7ekler a\u00e7ar \u266a",
    ],
    "rus": [
        "\u042f \u043d\u0435 \u0437\u043d\u0430\u044e, \u043e \u0447\u0451\u043c \u0442\u044b \u0433\u043e\u0432\u043e\u0440\u0438\u0448\u044c.",
        "\u0427\u0442\u043e \u0441\u043b\u0443\u0447\u0438\u043b\u043e\u0441\u044c \u0432\u0447\u0435\u0440\u0430 \u043d\u043e\u0447\u044c\u044e?",
        "\u041e\u0442\u043a\u0440\u043e\u0439 \u0434\u0432\u0435\u0440\u044c!",
        "\u042d\u0442\u043e \u043d\u0435 \u043c\u043e\u0436\u0435\u0442 \u0431\u044b\u0442\u044c \u043f\u0440\u0430\u0432\u0434\u043e\u0439.",
        "- \u0422\u044b \u0443\u0432\u0435\u0440\u0435\u043d?  - \u041a\u043e\u043d\u0435\u0447\u043d\u043e.",
        "\u0414\u043e \u0441\u0432\u0438\u0434\u0430\u043d\u0438\u044f.",
        "\u0421\u043f\u0430\u0441\u0438\u0431\u043e \u0437\u0430 \u0432\u0441\u0451.",
        "\u042f \u0442\u043e\u0436\u0435 \u0442\u0435\u0431\u044f \u043b\u044e\u0431\u043b\u044e.",
        "\u041c\u044b \u0441\u043f\u0440\u0430\u0432\u0438\u043b\u0438\u0441\u044c.",
        "\u0412\u0441\u0451 \u043a\u043e\u043d\u0447\u0435\u043d\u043e.",
        "[ \u0414\u0432\u0435\u0440\u044c \u0441\u043a\u0440\u0438\u043f\u0438\u0442 ]",
        "( \u0432\u0437\u0434\u044b\u0445\u0430\u0435\u0442 )",
        "\u0413\u0434\u0435 \u0442\u044b?",
        "\u041f\u0440\u043e\u0441\u0442\u0438, \u043c\u043e\u0436\u0435\u0448\u044c \u043f\u043e\u0432\u0442\u043e\u0440\u0438\u0442\u044c?",
        "\u041c\u043e\u0441\u043a\u0432\u0430 \u2014 \u043a\u0440\u0430\u0441\u0438\u0432\u044b\u0439 \u0433\u043e\u0440\u043e\u0434.",
        "\u0421\u0435\u0439\u0447\u0430\u0441 \u0437\u0438\u043c\u0430, \u0438\u0434\u0451\u0442 \u0441\u043d\u0435\u0433.",
        "\u0429\u0435\u043d\u043e\u043a \u0438\u0433\u0440\u0430\u0435\u0442 \u0432\u043e \u0434\u0432\u043e\u0440\u0435.",
        "\u042a\u0435\u0437\u0434 \u0431\u044b\u043b \u043e\u043f\u0430\u0441\u043d\u044b\u043c.",
        "\u266a \u041a\u0430\u0442\u044e\u0448\u0430 \u0432\u044b\u0445\u043e\u0434\u0438\u043b\u0430 \u043d\u0430 \u0431\u0435\u0440\u0435\u0433 \u266a",
    ],
    "ukr": [
        "\u042f \u043d\u0435 \u0437\u043d\u0430\u044e, \u043f\u0440\u043e \u0449\u043e \u0442\u0438 \u0433\u043e\u0432\u043e\u0440\u0438\u0448.",
        "\u0429\u043e \u0441\u0442\u0430\u043b\u043e\u0441\u044f \u0432\u0447\u043e\u0440\u0430 \u0432\u043d\u043e\u0447\u0456?",
        "\u0412\u0456\u0434\u0447\u0438\u043d\u0438 \u0434\u0432\u0435\u0440\u0456!",
        "\u0426\u0435 \u043d\u0435 \u043c\u043e\u0436\u0435 \u0431\u0443\u0442\u0438 \u043f\u0440\u0430\u0432\u0434\u043e\u044e.",
        "- \u0422\u0438 \u0432\u043f\u0435\u0432\u043d\u0435\u043d\u0438\u0439?  - \u0417\u0432\u0438\u0447\u0430\u0439\u043d\u043e.",
        "\u0414\u043e \u043f\u043e\u0431\u0430\u0447\u0435\u043d\u043d\u044f.",
        "\u0414\u044f\u043a\u0443\u044e \u0437\u0430 \u0432\u0441\u0435.",
        "\u042f \u0442\u0435\u0436 \u0442\u0435\u0431\u0435 \u043a\u043e\u0445\u0430\u044e.",
        "\u041c\u0438 \u0432\u043f\u043e\u0440\u0430\u043b\u0438\u0441\u044f.",
        "\u0412\u0441\u0435 \u0437\u0430\u043a\u0456\u043d\u0447\u0438\u043b\u043e\u0441\u044c.",
        "\u0414\u0435 \u0442\u0438?",
        "\u041a\u0438\u0457\u0432 \u2014 \u0433\u0430\u0440\u043d\u0435 \u043c\u0456\u0441\u0442\u043e.",
        "\u0411\u0443\u0434\u044c \u043b\u0430\u0441\u043a\u0430, \u0434\u043e\u043f\u043e\u043c\u043e\u0436\u0456\u0442\u044c \u043c\u0435\u043d\u0456.",
        "\u0407\u0436\u0430\u043a \u043f\u043e\u0432\u0437 \u043b\u0456\u0441\u043e\u043c.",
        "\u0490\u0430\u043d\u043e\u043a \u0432\u0438\u0441\u0456\u0442\u044c \u043d\u0430 \u0441\u0442\u0456\u043d\u0456.",
        "\u266a \u0427\u0435\u0440\u0432\u043e\u043d\u0430 \u043a\u0430\u043b\u0438\u043d\u0430 \u266a",
    ],
    "bul": [
        "\u041d\u0435 \u0437\u043d\u0430\u043c \u0437\u0430 \u043a\u0430\u043a\u0432\u043e \u0433\u043e\u0432\u043e\u0440\u0438\u0448.",
        "\u041a\u0430\u043a\u0432\u043e \u0441\u0442\u0430\u043d\u0430 \u0441\u043d\u043e\u0449\u0438?",
        "\u041e\u0442\u0432\u043e\u0440\u0438 \u0432\u0440\u0430\u0442\u0430\u0442\u0430!",
        "\u0422\u043e\u0432\u0430 \u043d\u0435 \u043c\u043e\u0436\u0435 \u0434\u0430 \u0435 \u0432\u044f\u0440\u043d\u043e.",
        "- \u0421\u0438\u0433\u0443\u0440\u0435\u043d \u043b\u0438 \u0441\u0438?  - \u0420\u0430\u0437\u0431\u0438\u0440\u0430 \u0441\u0435.",
        "\u0414\u043e\u0432\u0438\u0436\u0434\u0430\u043d\u0435.",
        "\u0411\u043b\u0430\u0433\u043e\u0434\u0430\u0440\u044f \u0437\u0430 \u0432\u0441\u0438\u0447\u043a\u043e.",
        "\u0418 \u0430\u0437 \u0442\u0435 \u043e\u0431\u0438\u0447\u0430\u043c.",
        "\u0423\u0441\u043f\u044f\u0445\u043c\u0435.",
        "\u041a\u0440\u0430\u044f\u0442.",
        "\u0421\u043e\u0444\u0438\u044f \u0435 \u0441\u0442\u043e\u043b\u0438\u0446\u0430\u0442\u0430 \u043d\u0430 \u0411\u044a\u043b\u0433\u0430\u0440\u0438\u044f.",
        "\u0429\u0435 \u0441\u0435 \u0432\u0438\u0434\u0438\u043c \u0443\u0442\u0440\u0435.",
        "\u266a \u0425\u0443\u0431\u0430\u0432\u0430 \u0441\u0438, \u043c\u043e\u044f \u0433\u043e\u0440\u043e \u266a",
    ],
    "ell": [
        "\u0394\u03b5\u03bd \u03be\u03ad\u03c1\u03c9 \u03b3\u03b9\u03b1 \u03c4\u03b9 \u03bc\u03b9\u03bb\u03ac\u03c2.",
        "\u0394\u03b5\u03bd \u03bc\u03c0\u03bf\u03c1\u03b5\u03af \u03bd\u03b1 \u03b5\u03af\u03bd\u03b1\u03b9 \u03b1\u03bb\u03ae\u03b8\u03b5\u03b9\u03b1.",
        "\u0386\u03bd\u03bf\u03b9\u03be\u03b5 \u03c4\u03b7\u03bd \u03c0\u03cc\u03c1\u03c4\u03b1!",
        "- \u0395\u03af\u03c3\u03b1\u03b9 \u03c3\u03af\u03b3\u03bf\u03c5\u03c1\u03bf\u03c2;  - \u0391\u03c0\u03cc\u03bb\u03c5\u03c4\u03b1.",
        "\u0391\u03bd\u03c4\u03af\u03bf.",
        "\u0395\u03c5\u03c7\u03b1\u03c1\u03b9\u03c3\u03c4\u03ce \u03b3\u03b9\u03b1 \u03cc\u03bb\u03b1.",
        "\u039a\u03b9 \u03b5\u03b3\u03ce \u03c3\u2019 \u03b1\u03b3\u03b1\u03c0\u03ce.",
        "\u03a4\u03b1 \u03ba\u03b1\u03c4\u03b1\u03c6\u03ad\u03c1\u03b1\u03bc\u03b5.",
        "\u03a4\u03ad\u03bb\u03b5\u03b9\u03c9\u03c3\u03b5.",
        "\u03a0\u03bf\u03cd \u03b5\u03af\u03c3\u03b1\u03b9;",
        "\u0397 \u0391\u03b8\u03ae\u03bd\u03b1 \u03b5\u03af\u03bd\u03b1\u03b9 \u03c0\u03b1\u03bd\u03ad\u03bc\u03bf\u03c1\u03c6\u03b7.",
        "\u03a4\u03bf \u03c6\u03b8\u03b9\u03bd\u03cc\u03c0\u03c9\u03c1\u03bf \u03ae\u03c1\u03b8\u03b5.",
        "\u03a8\u03ac\u03c7\u03bd\u03c9 \u03c4\u03bf\u03bd \u03b1\u03b4\u03b5\u03c1\u03c6\u03cc \u03bc\u03bf\u03c5.",
        "\u266a \u039d\u03cd\u03c7\u03c4\u03b5\u03c2 \u03c3\u03c4\u03b7\u03bd \u0391\u03b8\u03ae\u03bd\u03b1 \u266a",
    ],
    "jpn": [
        "\u4f55\u3092\u8a00\u3063\u3066\u3044\u308b\u306e\u304b\u5206\u304b\u3089\u306a\u3044\u3002",
        "\u6628\u591c\u4f55\u304c\u3042\u3063\u305f\uff1f",
        "\u30c9\u30a2\u3092\u958b\u3051\u3066\uff01",
        "\u305d\u3093\u306a\u308f\u3051\u304c\u306a\u3044\u3002",
        "\u300c\u672c\u5f53\u306b\uff1f\u300d\u300c\u3082\u3061\u308d\u3093\u3002\u300d",
        "\u3055\u3088\u306a\u3089\u3002",
        "\u3042\u308a\u304c\u3068\u3046\u3054\u3056\u3044\u307e\u3057\u305f\u3002",
        "\u79c1\u3082\u611b\u3057\u3066\u3044\u307e\u3059\u3002",
        "\u3084\u3063\u305f\uff01",
        "\u7d42\u308f\u3063\u305f\u3002",
        "\u3069\u3053\u306b\u3044\u308b\u306e\uff1f",
        "\u6771\u4eac\u306f\u7f8e\u3057\u3044\u8857\u3067\u3059\u3002",
        "\u660e\u65e5\u306f\u5929\u6c17\u304c\u826f\u3044\u3067\u3057\u3087\u3046\u3002",
        "\u30ab\u30bf\u30ab\u30ca\u3068\u3072\u3089\u304c\u306a\u3092\u7df4\u7fd2\u3057\u307e\u3059\u3002",
        "\u266a \u3055\u304f\u3089\u3055\u304f\u3089 \u266a",
    ],
    "kor": [
        "\ubb34\uc2a8 \ub9d0\uc744 \ud558\ub294 \uac74\uc9c0 \ubaa8\ub974\uaca0\uc5b4.",
        "\uc5b4\uc82f\ubc24\uc5d0 \ubb34\uc2a8 \uc77c\uc774 \uc788\uc5c8\uc5b4?",
        "\ubb38\uc744 \uc5f4\uc5b4!",
        "\uadf8\ub7f4 \ub9ac\uac00 \uc5c6\uc5b4.",
        "\ud655\uc2e4\ud574? \ubb3c\ub860\uc774\uc9c0.",
        "\uc548\ub155\ud788 \uac00\uc138\uc694.",
        "\ubaa8\ub4e0 \uac83\uc5d0 \uac10\uc0ac\ud569\ub2c8\ub2e4.",
        "\ub098\ub3c4 \uc0ac\ub791\ud574.",
        "\ud574\ub0c8\ub2e4!",
        "\ub05d\ub0ac\ub2e4.",
        "\uc5b4\ub514\uc57c?",
        "\uc11c\uc6b8\uc740 \uc544\ub984\ub2e4\uc6b4 \ub3c4\uc2dc\uc785\ub2c8\ub2e4.",
        "\ub0b4\uc77c \ubd10\uc694.",
        "\u266a \uc544\ub9ac\ub791 \u266a",
    ],
    "chi_sim": [
        "\u6211\u4e0d\u77e5\u9053\u4f60\u5728\u8bf4\u4ec0\u4e48\u3002",
        "\u6628\u665a\u53d1\u751f\u4e86\u4ec0\u4e48\uff1f",
        "\u5f00\u95e8\uff01",
        "\u8fd9\u4e0d\u53ef\u80fd\u662f\u771f\u7684\u3002",
        "\u201c\u4f60\u786e\u5b9a\u5417\uff1f\u201d\u201c\u5f53\u7136\u3002\u201d",
        "\u518d\u89c1\u3002",
        "\u8c22\u8c22\u4f60\u7684\u4e00\u5207\u3002",
        "\u6211\u4e5f\u7231\u4f60\u3002",
        "\u6211\u4eec\u505a\u5230\u4e86\u3002",
        "\u7ed3\u675f\u4e86\u3002",
        "\u4f60\u5728\u54ea\u91cc\uff1f",
        "\u5317\u4eac\u662f\u4e2d\u56fd\u7684\u9996\u90fd\u3002",
        "\u660e\u5929\u5929\u6c14\u4f1a\u5f88\u597d\u3002",
        "\u266a \u6708\u4eae\u4ee3\u8868\u6211\u7684\u5fc3 \u266a",
    ],
    "chi_tra": [
        "\u6211\u4e0d\u77e5\u9053\u4f60\u5728\u8aaa\u4ec0\u9ebc\u3002",
        "\u6628\u665a\u767c\u751f\u4e86\u4ec0\u9ebc\uff1f",
        "\u958b\u9580\uff01",
        "\u9019\u4e0d\u53ef\u80fd\u662f\u771f\u7684\u3002",
        "\u300c\u4f60\u78ba\u5b9a\u55ce\uff1f\u300d\u300c\u7576\u7136\u3002\u300d",
        "\u518d\u898b\u3002",
        "\u8b1d\u8b1d\u4f60\u7684\u4e00\u5207\u3002",
        "\u6211\u4e5f\u611b\u4f60\u3002",
        "\u6211\u5011\u505a\u5230\u4e86\u3002",
        "\u7d50\u675f\u4e86\u3002",
        "\u4f60\u5728\u54ea\u88e1\uff1f",
        "\u53f0\u5317\u662f\u500b\u7f8e\u9e97\u7684\u57ce\u5e02\u3002",
        "\u660e\u5929\u5929\u6c23\u6703\u5f88\u597d\u3002",
        "\u266a \u6708\u4eae\u4ee3\u8868\u6211\u7684\u5fc3 \u266a",
    ],
    "ara": [
        "\u0644\u0627 \u0623\u0639\u0631\u0641 \u0639\u0645\u0627 \u062a\u062a\u062d\u062f\u062b.",
        "\u0645\u0627\u0630\u0627 \u062d\u062f\u062b \u0627\u0644\u0628\u0627\u0631\u062d\u0629 \u0644\u064a\u0644\u0627\u064b\u061f",
        "\u0627\u0641\u062a\u062d \u0627\u0644\u0628\u0627\u0628!",
        "\u0647\u0630\u0627 \u0644\u0627 \u064a\u0645\u0643\u0646 \u0623\u0646 \u064a\u0643\u0648\u0646 \u0635\u062d\u064a\u062d\u0627\u064b.",
        "\u0647\u0644 \u0623\u0646\u062a \u0645\u062a\u0623\u0643\u062f\u061f \u0628\u0627\u0644\u062a\u0623\u0643\u064a\u062f.",
        "\u0645\u0639 \u0627\u0644\u0633\u0644\u0627\u0645\u0629.",
        "\u0634\u0643\u0631\u0627\u064b \u0639\u0644\u0649 \u0643\u0644 \u0634\u064a\u0621.",
        "\u0648\u0623\u0646\u0627 \u0623\u064a\u0636\u0627\u064b \u0623\u062d\u0628\u0643.",
        "\u0644\u0642\u062f \u0646\u062c\u062d\u0646\u0627.",
        "\u0627\u0646\u062a\u0647\u0649 \u0627\u0644\u0623\u0645\u0631.",
        "\u0623\u064a\u0646 \u0623\u0646\u062a\u061f",
        "\u0627\u0644\u0642\u0627\u0647\u0631\u0629 \u0645\u062f\u064a\u0646\u0629 \u062c\u0645\u064a\u0644\u0629.",
        "\u0633\u0623\u0631\u0627\u0643 \u063a\u062f\u0627\u064b.",
        "\u266a \u064a\u0627 \u0644\u064a\u0644 \u064a\u0627 \u0639\u064a\u0646 \u266a",
    ],
    "fas": [
        "\u0646\u0645\u06cc\u200c\u062f\u0627\u0646\u0645 \u062f\u0631\u0628\u0627\u0631\u0647 \u0686\u06cc \u062d\u0631\u0641 \u0645\u06cc\u200c\u0632\u0646\u06cc.",
        "\u062f\u06cc\u0634\u0628 \u0686\u0647 \u0627\u062a\u0641\u0627\u0642\u06cc \u0627\u0641\u062a\u0627\u062f\u061f",
        "\u062f\u0631 \u0631\u0627 \u0628\u0627\u0632 \u06a9\u0646!",
        "\u0627\u06cc\u0646 \u0646\u0645\u06cc\u200c\u062a\u0648\u0627\u0646\u062f \u062d\u0642\u06cc\u0642\u062a \u062f\u0627\u0634\u062a\u0647 \u0628\u0627\u0634\u062f.",
        "\u0645\u0637\u0645\u0626\u0646\u06cc\u061f \u0628\u0644\u0647.",
        "\u062e\u062f\u0627\u062d\u0627\u0641\u0638.",
        "\u0628\u0631\u0627\u06cc \u0647\u0645\u0647 \u0686\u06cc\u0632 \u0645\u0645\u0646\u0648\u0646\u0645.",
        "\u0645\u0646 \u0647\u0645 \u062f\u0648\u0633\u062a\u062a \u062f\u0627\u0631\u0645.",
        "\u0645\u0648\u0641\u0642 \u0634\u062f\u06cc\u0645.",
        "\u062a\u0645\u0627\u0645 \u0634\u062f.",
        "\u06a9\u062c\u0627\u06cc\u06cc\u061f",
        "\u062a\u0647\u0631\u0627\u0646 \u0634\u0647\u0631 \u0628\u0632\u0631\u06af\u06cc \u0627\u0633\u062a.",
        "\u0641\u0631\u062f\u0627 \u0645\u06cc\u200c\u0628\u06cc\u0646\u0645\u062a.",
        "\u0627\u06cc\u0646 \u06af\u0644 \u067e\u0698\u0645\u0631\u062f\u0647 \u0627\u0633\u062a.",
    ],
    "heb": [
        "\u05d0\u05e0\u05d9 \u05dc\u05d0 \u05d9\u05d5\u05d3\u05e2 \u05e2\u05dc \u05de\u05d4 \u05d0\u05ea\u05d4 \u05de\u05d3\u05d1\u05e8.",
        "\u05de\u05d4 \u05e7\u05e8\u05d4 \u05d0\u05de\u05e9 \u05d1\u05dc\u05d9\u05dc\u05d4?",
        "\u05ea\u05e4\u05ea\u05d7 \u05d0\u05ea \u05d4\u05d3\u05dc\u05ea!",
        "\u05d6\u05d4 \u05dc\u05d0 \u05d9\u05db\u05d5\u05dc \u05dc\u05d4\u05d9\u05d5\u05ea \u05e0\u05db\u05d5\u05df.",
        "\u05d0\u05ea\u05d4 \u05d1\u05d8\u05d5\u05d7? \u05d1\u05d4\u05d7\u05dc\u05d8.",
        "\u05dc\u05d4\u05ea\u05e8\u05d0\u05d5\u05ea.",
        "\u05ea\u05d5\u05d3\u05d4 \u05e2\u05dc \u05d4\u05db\u05dc.",
        "\u05d2\u05dd \u05d0\u05e0\u05d9 \u05d0\u05d5\u05d4\u05d1 \u05d0\u05d5\u05ea\u05da.",
        "\u05e2\u05e9\u05d9\u05e0\u05d5 \u05d0\u05ea \u05d6\u05d4.",
        "\u05d6\u05d4 \u05e0\u05d2\u05de\u05e8.",
        "\u05d0\u05d9\u05e4\u05d4 \u05d0\u05ea\u05d4?",
        "\u05d9\u05e8\u05d5\u05e9\u05dc\u05d9\u05dd \u05d4\u05d9\u05d0 \u05e2\u05d9\u05e8 \u05d9\u05e4\u05d4.",
        "\u05e0\u05ea\u05e8\u05d0\u05d4 \u05de\u05d7\u05e8.",
        "\u266a \u05d4\u05d1\u05d4 \u05e0\u05d2\u05d9\u05dc\u05d4 \u266a",
    ],
    "hin": [
        "\u092e\u0941\u091d\u0947 \u0928\u0939\u0940\u0902 \u092a\u0924\u093e \u0924\u0941\u092e \u0915\u094d\u092f\u093e \u0915\u0939 \u0930\u0939\u0947 \u0939\u094b\u0964",
        "\u0915\u0932 \u0930\u093e\u0924 \u0915\u094d\u092f\u093e \u0939\u0941\u0906?",
        "\u0926\u0930\u0935\u093e\u091c\u093c\u093e \u0916\u094b\u0932\u094b!",
        "\u092f\u0939 \u0938\u091a \u0928\u0939\u0940\u0902 \u0939\u094b \u0938\u0915\u0924\u093e\u0964",
        "\u0915\u094d\u092f\u093e \u0924\u0941\u092e \u092a\u0915\u094d\u0915\u0947 \u0939\u094b? \u092c\u093f\u0932\u0915\u0941\u0932\u0964",
        "\u0905\u0932\u0935\u093f\u0926\u093e\u0964",
        "\u0938\u092c \u0915\u0947 \u0932\u093f\u090f \u0927\u0928\u094d\u092f\u0935\u093e\u0926\u0964",
        "\u092e\u0948\u0902 \u092d\u0940 \u0924\u0941\u092e\u0938\u0947 \u092a\u094d\u092f\u093e\u0930 \u0915\u0930\u0924\u093e \u0939\u0942\u0901\u0964",
        "\u0939\u092e\u0928\u0947 \u0915\u0930 \u0926\u093f\u0916\u093e\u092f\u093e\u0964",
        "\u0916\u0924\u094d\u092e \u0939\u094b \u0917\u092f\u093e\u0964",
        "\u0924\u0941\u092e \u0915\u0939\u093e\u0901 \u0939\u094b?",
        "\u0926\u093f\u0932\u094d\u0932\u0940 \u092c\u0939\u0941\u0924 \u0938\u0941\u0902\u0926\u0930 \u0936\u0939\u0930 \u0939\u0948\u0964",
        "\u0915\u0932 \u092e\u093f\u0932\u0947\u0902\u0917\u0947\u0964",
        "\u266a \u091c\u092f \u0939\u094b \u266a",
    ],
    "ben": [
        "\u0986\u09ae\u09bf \u099c\u09be\u09a8\u09bf \u09a8\u09be \u09a4\u09c1\u09ae\u09bf \u0995\u09c0 \u09ac\u09b2\u099b\u09cb\u0964",
        "\u0997\u09a4 \u09b0\u09be\u09a4\u09c7 \u0995\u09c0 \u09b9\u09df\u09c7\u099b\u09bf\u09b2?",
        "\u09a6\u09b0\u099c\u09be \u0996\u09cb\u09b2\u09cb!",
        "\u098f\u099f\u09be \u09b8\u09a4\u09cd\u09af\u09bf \u09b9\u09a4\u09c7 \u09aa\u09be\u09b0\u09c7 \u09a8\u09be\u0964",
        "\u09a4\u09c1\u09ae\u09bf \u0995\u09bf \u09a8\u09bf\u09b6\u09cd\u099a\u09bf\u09a4? \u0985\u09ac\u09b6\u09cd\u09af\u0987\u0964",
        "\u09ac\u09bf\u09a6\u09be\u09df\u0964",
        "\u09b8\u09ac\u0995\u09bf\u099b\u09c1\u09b0 \u099c\u09a8\u09cd\u09af \u09a7\u09a8\u09cd\u09af\u09ac\u09be\u09a6\u0964",
        "\u0986\u09ae\u09bf\u0993 \u09a4\u09cb\u09ae\u09be\u09df \u09ad\u09be\u09b2\u09cb\u09ac\u09be\u09b8\u09bf\u0964",
        "\u0986\u09ae\u09b0\u09be \u09aa\u09c7\u09b0\u09c7\u099b\u09bf\u0964",
        "\u09b6\u09c7\u09b7 \u09b9\u09df\u09c7\u099b\u09c7\u0964",
        "\u09a4\u09c1\u09ae\u09bf \u0995\u09cb\u09a5\u09be\u09df?",
        "\u0995\u09b2\u0995\u09be\u09a4\u09be \u098f\u0995\u099f\u09bf \u09ac\u09bf\u09b6\u09be\u09b2 \u09b6\u09b9\u09b0\u0964",
        "\u266a \u09b0\u09ac\u09c0\u09a8\u09cd\u09a6\u09cd\u09b0\u09a8\u09be\u09a5 \u266a",
    ],
    "tam": [
        "\u0ba8\u0bc0 \u0b8e\u0ba9\u0bcd\u0ba9 \u0b9a\u0bca\u0bb2\u0bcd\u0bb2\u0bbf\u0b95\u0bcd\u0b95\u0bbf\u0bb1\u0bbe\u0baf\u0bcd \u0ba4\u0bc6\u0bb0\u0bbf\u0baf\u0bb5\u0bbf\u0bb2\u0bcd\u0bb2\u0bc8.",
        "\u0ba8\u0bc7\u0bb1\u0bcd\u0bb1\u0bbf\u0bb0\u0bb5\u0bc1 \u0b8e\u0ba9\u0bcd\u0ba9 \u0ba8\u0b9f\u0ba8\u0bcd\u0ba4\u0ba4\u0bc1?",
        "\u0b95\u0ba4\u0bb5\u0bc8\u0ba4\u0bcd \u0ba4\u0bbf\u0bb1!",
        "\u0b87\u0ba4\u0bc1 \u0b89\u0ba3\u0bcd\u0bae\u0bc8\u0baf\u0bbe\u0b95 \u0b87\u0bb0\u0bc1\u0b95\u0bcd\u0b95 \u0bae\u0bc1\u0b9f\u0bbf\u0baf\u0bbe\u0ba4\u0bc1.",
        "\u0bb5\u0ba3\u0b95\u0bcd\u0b95\u0bae\u0bcd.",
        "\u0ba8\u0ba9\u0bcd\u0bb1\u0bbf.",
        "\u0ba8\u0bbe\u0ba9\u0bc1\u0bae\u0bcd \u0b89\u0ba9\u0bcd\u0ba9\u0bc8 \u0b95\u0bbe\u0ba4\u0bb2\u0bbf\u0b95\u0bcd\u0b95\u0bbf\u0bb1\u0bc7\u0ba9\u0bcd.",
        "\u0b9a\u0bc6\u0ba9\u0bcd\u0ba9\u0bc8 \u0b85\u0bb4\u0b95\u0bbe\u0ba9 \u0ba8\u0b95\u0bb0\u0bae\u0bcd.",
        "\u266a \u0ba4\u0bae\u0bbf\u0bb4\u0bcd \u0ba4\u0bae\u0bbf\u0bb4\u0bcd \u266a",
    ],
    "tha": [
        "\u0e09\u0e31\u0e19\u0e44\u0e21\u0e48\u0e23\u0e39\u0e49\u0e27\u0e48\u0e32\u0e04\u0e38\u0e13\u0e1e\u0e39\u0e14\u0e40\u0e23\u0e37\u0e48\u0e2d\u0e07\u0e2d\u0e30\u0e44\u0e23",
        "\u0e40\u0e21\u0e37\u0e48\u0e2d\u0e04\u0e37\u0e19\u0e21\u0e35\u0e2d\u0e30\u0e44\u0e23\u0e40\u0e01\u0e34\u0e14\u0e02\u0e36\u0e49\u0e19?",
        "\u0e40\u0e1b\u0e34\u0e14\u0e1b\u0e23\u0e30\u0e15\u0e39!",
        "\u0e19\u0e35\u0e48\u0e44\u0e21\u0e48\u0e2d\u0e32\u0e08\u0e40\u0e1b\u0e47\u0e19\u0e04\u0e27\u0e32\u0e21\u0e08\u0e23\u0e34\u0e07\u0e44\u0e14\u0e49",
        "\u0e41\u0e19\u0e48\u0e43\u0e08\u0e40\u0e2b\u0e23\u0e2d? \u0e41\u0e19\u0e48\u0e19\u0e2d\u0e19.",
        "\u0e25\u0e32\u0e01\u0e48\u0e2d\u0e19",
        "\u0e02\u0e2d\u0e1a\u0e04\u0e38\u0e13\u0e2a\u0e33\u0e2b\u0e23\u0e31\u0e1a\u0e17\u0e38\u0e01\u0e2d\u0e22\u0e48\u0e32\u0e07",
        "\u0e09\u0e31\u0e19\u0e23\u0e31\u0e01\u0e04\u0e38\u0e13\u0e40\u0e2b\u0e21\u0e37\u0e2d\u0e19\u0e01\u0e31\u0e19",
        "\u0e40\u0e23\u0e32\u0e17\u0e33\u0e44\u0e14\u0e49\u0e41\u0e25\u0e49\u0e27",
        "\u0e08\u0e1a\u0e41\u0e25\u0e49\u0e27",
        "\u0e04\u0e38\u0e13\u0e2d\u0e22\u0e39\u0e48\u0e44\u0e2b\u0e19?",
        "\u0e01\u0e23\u0e38\u0e07\u0e40\u0e17\u0e1e\u0e40\u0e1b\u0e47\u0e19\u0e40\u0e21\u0e37\u0e2d\u0e07\u0e17\u0e35\u0e48\u0e2a\u0e27\u0e22\u0e07\u0e32\u0e21",
        "\u266a \u0e25\u0e2d\u0e22\u0e01\u0e23\u0e30\u0e17\u0e07 \u266a",
    ],
    "vie": [
        "T\u00f4i kh\u00f4ng bi\u1ebft b\u1ea1n \u0111ang n\u00f3i g\u00ec.",
        "\u0110\u00eam qua \u0111\u00e3 x\u1ea3y ra chuy\u1ec7n g\u00ec?",
        "M\u1edf c\u1eeda ra!",
        "\u0110i\u1ec1u n\u00e0y kh\u00f4ng th\u1ec3 \u0111\u00fang \u0111\u01b0\u1ee3c.",
        "B\u1ea1n ch\u1eafc ch\u1ee9? Ch\u1eafc ch\u1eafn.",
        "T\u1ea1m bi\u1ec7t.",
        "C\u1ea3m \u01a1n v\u00ec t\u1ea5t c\u1ea3.",
        "T\u00f4i c\u0169ng y\u00eau b\u1ea1n.",
        "Ch\u00fang ta \u0111\u00e3 l\u00e0m \u0111\u01b0\u1ee3c.",
        "K\u1ebft th\u00fac r\u1ed3i.",
        "B\u1ea1n \u1edf \u0111\u00e2u?",
        "H\u00e0 N\u1ed9i l\u00e0 th\u1ee7 \u0111\u00f4 c\u1ee7a Vi\u1ec7t Nam.",
        "H\u1eb9n g\u1eb7p l\u1ea1i.",
        "\u266a Tr\u1ecbnh C\u00f4ng S\u01a1n \u266a",
    ],
    "ind": [
        "Saya tidak tahu apa yang kamu bicarakan.",
        "Apa yang terjadi semalam?",
        "Buka pintunya!",
        "Ini tidak mungkin benar.",
        "Kamu yakin? Tentu saja.",
        "Selamat tinggal.",
        "Terima kasih untuk semuanya.",
        "Aku juga mencintaimu.",
        "Kita berhasil.",
        "Sudah selesai.",
        "Kamu di mana?",
        "Jakarta adalah kota yang besar.",
        "Sampai jumpa besok.",
    ],
    "msa": [
        "Saya tidak tahu apa yang awak cakap.",
        "Apa yang berlaku semalam?",
        "Buka pintu!",
        "Ini tidak mungkin benar.",
        "Awak pasti? Sudah tentu.",
        "Selamat tinggal.",
        "Terima kasih untuk semuanya.",
        "Saya juga sayang awak.",
        "Kita berjaya.",
        "Sudah tamat.",
        "Awak di mana?",
        "Kuala Lumpur ialah bandar raya yang indah.",
        "Jumpa lagi esok.",
    ],
    "isl": [
        "\u00c9g veit ekki hva\u00f0 \u00fe\u00fa ert a\u00f0 tala um.",
        "Hva\u00f0 ger\u00f0ist \u00ed g\u00e6rkveld?",
        "Opna\u00f0u dyrnar!",
        "\u00deetta getur ekki veri\u00f0 satt.",
        "Ertu viss? Algjerlega.",
        "Bless.",
        "\u00deakka \u00fe\u00e9r fyrir allt.",
        "\u00c9g elska \u00feig l\u00edka.",
        "Vi\u00f0 n\u00e1\u00f0um \u00feessu.",
        "\u00dea\u00f0 er b\u00fai\u00f0.",
        "Hvar ertu?",
        "Reykjav\u00edk er falleg borg.",
        "\u00cdslenskan hefur s\u00e9rstaka stafi: \u00fe, \u00f0, \u00e6.",
        "\u266a \u00d3, gu\u00f0 vors lands \u266a",
    ],
    "hrv": [
        "Ne znam o \u010demu pri\u010da\u0161.",
        "\u0160to se dogodilo sino\u0107?",
        "Otvori vrata!",
        "To ne mo\u017ee biti istina.",
        "Jesi li siguran? Naravno.",
        "Dovi\u0111enja.",
        "Hvala na svemu.",
        "I ja te volim.",
        "Uspjeli smo.",
        "Gotovo je.",
        "Gdje si?",
        "Zagreb je lijep grad.",
        "\u017divot je kompliciran.",
        "\u0106u\u0107ukovi\u0107 je \u010duveni pisac.",
        "\u266a Lijepa na\u0161a domovino \u266a",
    ],
    "srp_latn": [
        "Ne znam o \u010demu pri\u010da\u0161.",
        "\u0160ta se desilo sino\u0107?",
        "Otvori vrata!",
        "To ne mo\u017ee biti istina.",
        "Jesi li siguran? Naravno.",
        "Dovi\u0111enja.",
        "Hvala na svemu.",
        "I ja te volim.",
        "Uspeli smo.",
        "Gotovo je.",
        "Gde si?",
        "Beograd je lep grad.",
        "\u017divot je komplikovan.",
        "\u0110or\u0111e Pe\u0107anac je bio tu.",
        "\u266a Ta\u0161majdan \u266a",
    ],
    "srp": [
        "\u041d\u0435 \u0437\u043d\u0430\u043c \u043e \u0447\u0435\u043c\u0443 \u043f\u0440\u0438\u0447\u0430\u0448.",
        "\u0428\u0442\u0430 \u0441\u0435 \u0434\u0435\u0441\u0438\u043b\u043e \u0441\u0438\u043d\u043e\u045b?",
        "\u041e\u0442\u0432\u043e\u0440\u0438 \u0432\u0440\u0430\u0442\u0430!",
        "\u0422\u043e \u043d\u0435 \u043c\u043e\u0436\u0435 \u0431\u0438\u0442\u0438 \u0438\u0441\u0442\u0438\u043d\u0430.",
        "\u0414\u043e\u0432\u0438\u0452\u0435\u045a\u0430.",
        "\u0425\u0432\u0430\u043b\u0430 \u043d\u0430 \u0441\u0432\u0435\u043c\u0443.",
        "\u0418 \u0458\u0430 \u0442\u0435 \u0432\u043e\u043b\u0438\u043c.",
        "\u0423\u0441\u043f\u0435\u043b\u0438 \u0441\u043c\u043e.",
        "\u0413\u043e\u0442\u043e\u0432\u043e \u0458\u0435.",
        "\u0413\u0434\u0435 \u0441\u0438?",
        "\u0411\u0435\u043e\u0433\u0440\u0430\u0434 \u0458\u0435 \u043b\u0435\u043f \u0433\u0440\u0430\u0434.",
        "\u0416\u0438\u0432\u043e\u0442 \u0458\u0435 \u0441\u043b\u043e\u0436\u0435\u043d.",
        "\u0402\u0443\u0440\u0452\u0435 \u041f\u0435\u045b\u0430\u043d\u0430\u0446 \u0458\u0435 \u0431\u0438\u043e \u0442\u0443.",
    ],
    "slv": [
        "Ne vem, o \u010dem govori\u0161.",
        "Kaj se je zgodilo sino\u010di?",
        "Odpri vrata!",
        "To ne more biti res.",
        "Si prepri\u010dan? Seveda.",
        "Nasvidenje.",
        "Hvala za vse.",
        "Tudi jaz te imam rad.",
        "Uspelo nam je.",
        "Konec je.",
        "Kje si?",
        "Ljubljana je lepo mesto.",
        "\u017divljenje je zapleteno.",
        "\u0160e danes se bomo videli.",
        "\u010ce\u0161nje cvetijo \u017ee.",
        "\u266a Zdravljica \u266a",
    ],
    "sqi": [
        "Nuk e di p\u00ebr \u00e7far\u00eb po flet.",
        "\u00c7far\u00eb ndodhi mbr\u00ebm\u00eb?",
        "Hape der\u00ebn!",
        "Kjo nuk mund t\u00eb jet\u00eb e v\u00ebrtet\u00eb.",
        "Je i sigurt? Sigurisht.",
        "Mir\u00ebupafshim.",
        "Faleminderit p\u00ebr gjith\u00e7ka.",
        "Un\u00eb gjithashtu t\u00eb dua.",
        "Ia dol\u00ebm.",
        "Mbaroi.",
        "Ku je?",
        "Tirana \u00ebsht\u00eb nj\u00eb qytet i bukur.",
        "\u00cb\u0308sht\u00eb e pamundur.",
        "\u266a Hymni i Flamurit \u266a",
    ],
    "cat": [
        "No s\u00e9 de qu\u00e8 est\u00e0s parlant.",
        "Qu\u00e8 va passar anit?",
        "Obre la porta!",
        "Aix\u00f2 no pot ser veritat.",
        "N'est\u00e0s segur? Per descomptat.",
        "Ad\u00e9u.",
        "Gr\u00e0cies per tot.",
        "Jo tamb\u00e9 t'estimo.",
        "Ho hem aconseguit.",
        "S'ha acabat.",
        "On ets?",
        "Barcelona \u00e9s una ciutat preciosa.",
        "L'endem\u00e0 farà bon temps.",
        "\u266a Els Segadors \u266a",
    ],
    "kat": [
        "\u10d0\u10e0 \u10d5\u10d8\u10ea\u10d8 \u10e0\u10d0\u10d6\u10d4 \u10e1\u10d0\u10e3\u10d1\u10e0\u10dd\u10d1.",
        "\u10e0\u10d0 \u10db\u10dd\u10ee\u10d3\u10d0 \u10ec\u10e3\u10ee\u10d4\u10da \u10e6\u10d0\u10db\u10d8\u10d7?",
        "\u10d2\u10d0\u10d0\u10e6\u10d4 \u10d9\u10d0\u10e0\u10d8!",
        "\u10d4\u10e1 \u10e1\u10d8\u10db\u10d0\u10e0\u10d7\u10da\u10d4 \u10d0\u10e0 \u10e8\u10d4\u10d8\u10eb\u10da\u10d4\u10d1\u10d0.",
        "\u10d3\u10d0\u10e0\u10ec\u10db\u10e3\u10dc\u10d4\u10d1\u10e3\u10da\u10d8 \u10ee\u10d0\u10e0? \u10e0\u10d0 \u10d7\u10e5\u10db\u10d0 \u10e3\u10dc\u10d3\u10d0.",
        "\u10dc\u10d0\u10ee\u10d5\u10d0\u10db\u10d3\u10d8\u10e1.",
        "\u10db\u10d0\u10d3\u10da\u10dd\u10d1\u10d0 \u10e7\u10d5\u10d4\u10da\u10d0\u10e4\u10e0\u10d8\u10e1\u10d7\u10d5\u10d8\u10e1.",
        "\u10db\u10d4\u10ea \u10e8\u10d4\u10dc \u10db\u10d8\u10e7\u10d5\u10d0\u10e0\u10ee\u10d0\u10e0.",
        "\u10e8\u10d4\u10d5\u10d0\u10e4\u10d4\u10e0\u10d4\u10d7.",
        "\u10d3\u10d0\u10db\u10d7\u10d0\u10d5\u10e0\u10d3\u10d0.",
        "\u10e1\u10d0\u10d3 \u10ee\u10d0\u10e0?",
        "\u10d7\u10d1\u10d8\u10da\u10d8\u10e1\u10d8 \u10da\u10d0\u10db\u10d0\u10d6\u10d8 \u10e5\u10d0\u10da\u10d0\u10e5\u10d8\u10d0.",
        "\u266a \u10e1\u10d0\u10e5\u10d0\u10e0\u10d7\u10d5\u10d4\u10da\u10dd \u266a",
    ],
    "hye": [
        "\u0549\u0563\u056b\u057f\u0565\u0574 \u056b\u0576\u0579\u056b \u0574\u0561\u057d\u056b\u0576 \u0565\u057d \u056d\u0578\u057d\u0578\u0582\u0574.",
        "\u053b\u0576\u0579 \u057a\u0561\u057f\u0561\u0570\u0565\u0581 \u0565\u0580\u0565\u056f \u0563\u056b\u0577\u0565\u0580?",
        "\u0532\u0561\u0581\u056b\u0580 \u0564\u0578\u0582\u057c\u0568!",
        "\u054d\u0561 \u0579\u056b \u056f\u0561\u0580\u0578\u0572 \u0573\u056b\u0577\u057f \u056c\u056b\u0576\u0565\u056c.",
        "\u0540\u0561\u0574\u0578\u0566\u057e\u0561\u057e\u0561\u055e\u0535\u057e \u0561\u0575\u0564.",
        "\u0551\u057f\u0565\u057d\u0578\u0582\u0569\u0575\u0578\u0582\u0576.",
        "\u0547\u0576\u0578\u0580\u0570\u0561\u056f\u0561\u056c\u0578\u0582\u0569\u0575\u0578\u0582\u0576 \u0561\u0574\u0565\u0576 \u056b\u0576\u0579\u056b \u0570\u0561\u0574\u0561\u0580.",
        "\u0535\u057d \u0567\u056c \u0584\u0565\u0566 \u057d\u056b\u0580\u0578\u0582\u0574 \u0565\u0574.",
        "\u0544\u0565\u0576\u0584 \u0570\u0561\u057b\u0578\u0572\u0565\u0581\u056b\u0576\u0584.",
        "\u054e\u0565\u0580\u057b\u0561\u0581\u0561\u057e.",
        "\u0548\u0580\u057f\u0565\u0572 \u0565\u057d?",
        "\u0535\u0580\u0587\u0561\u0576\u0568 \u0563\u0565\u0572\u0565\u0581\u056b\u056f \u0584\u0561\u0572\u0561\u0584 \u0567.",
        "\u266a \u053f\u056b\u056c\u056b\u056f\u056b\u0561 \u266a",
    ],
}

# Aliases — languages sharing identical or near-identical scripts
LANG_SENTENCES["enm"] = LANG_SENTENCES["eng"]
LANG_SENTENCES["ger"] = LANG_SENTENCES["deu"]
LANG_SENTENCES["deu_frak"] = LANG_SENTENCES["deu"]
LANG_SENTENCES["deu_latf"] = LANG_SENTENCES["deu"]
LANG_SENTENCES["dut"] = LANG_SENTENCES["nld"]
LANG_SENTENCES["spa_old"] = LANG_SENTENCES["spa"]
LANG_SENTENCES["frm"] = LANG_SENTENCES["fra"]
LANG_SENTENCES["ita_old"] = LANG_SENTENCES["ita"]
LANG_SENTENCES["dan_frak"] = LANG_SENTENCES["dan"]
LANG_SENTENCES["slk_frak"] = LANG_SENTENCES["slk"]
LANG_SENTENCES["jpn_vert"] = LANG_SENTENCES["jpn"]
LANG_SENTENCES["kor_vert"] = LANG_SENTENCES["kor"]
LANG_SENTENCES["chi_sim_vert"] = LANG_SENTENCES["chi_sim"]
LANG_SENTENCES["chi_tra_vert"] = LANG_SENTENCES["chi_tra"]
LANG_SENTENCES["kat_old"] = LANG_SENTENCES["kat"]
LANG_SENTENCES["bos"] = LANG_SENTENCES["hrv"]


def build_training_lines(
    lang: str,
    chars: List[str],
    corpus_lines: List[str] | None = None,
    music_ratio: float = 0.30,
) -> List[str]:
    """
    Build the final training text for a language.

    Merges three sources:
    1. Corpus lines (real subtitle text from OpenSubtitles)
    2. LANG_SENTENCES (hand-crafted subtitle sentences)
    3. Music note injection (♪ bookends on random corpus lines)

    Target: ~30% of total lines contain ♪/♫ for music note training.
    """
    unique_lines: List[str] = []
    seen: Set[str] = set()
    rng = random.Random(42)

    def add(line: str) -> None:
        line = line.strip()
        if line and line not in seen:
            seen.add(line)
            unique_lines.append(line)

    # 1. Hand-crafted sentences (always included, high quality)
    for line in LANG_SENTENCES.get(lang, []):
        add(line)

    # 2. Corpus lines (bulk of training data)
    if corpus_lines:
        for line in corpus_lines:
            add(line)

    # 3. Music note injection — only when corpus data is NOT provided
    #    (corpus data from fetch_subtitle_corpus already has ♪ injected).
    #    When using LANG_SENTENCES only, inject ♪ to reach target ratio.
    if not corpus_lines:
        base_lines = list(unique_lines)
        if base_lines:
            current_music = sum(1 for l in base_lines if "\u266a" in l or "\u266b" in l)
            total = len(base_lines)
            target_music = int(total * music_ratio / (1.0 - music_ratio))
            needed = max(0, target_music - current_music)

            candidates = [l for l in base_lines if "\u266a" not in l and "\u266b" not in l
                           and len(l) >= 15]
            if candidates and needed > 0:
                for i in range(needed):
                    src = candidates[rng.randint(0, len(candidates) - 1)]
                    note = "\u266a" if i % 3 != 2 else "\u266b"
                    add(f"{note} {src} {note}")

    return unique_lines


# ── Output helpers ────────────────────────────────────────────────────────────

def write_training_text(
    lang: str,
    chars: List[str],
    output_dir: Path,
    corpus_lines: List[str] | None = None,
) -> Path:
    """Write <output_dir>/<lang>/<lang>.training_text and return the path."""
    lang_dir = output_dir / lang
    lang_dir.mkdir(parents=True, exist_ok=True)

    lines = build_training_lines(lang, chars, corpus_lines=corpus_lines)
    out_path = lang_dir / f"{lang}.training_text"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


def write_fonts_file(lang: str, output_dir: Path) -> Path:
    """Write <output_dir>/<lang>/<lang>.fonts and return the path."""
    lang_dir = output_dir / lang
    lang_dir.mkdir(parents=True, exist_ok=True)

    fonts = get_fonts_for_lang(lang)
    out_path = lang_dir / f"{lang}.fonts"
    out_path.write_text("\n".join(fonts) + "\n", encoding="utf-8")
    return out_path


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    root = repo_root()
    config_dir = root / "training" / "config"
    default_out = root / "training" / "generated"
    tessdata_dir = root / "tessdata"

    parser = argparse.ArgumentParser(
        description="Generate .training_text and .fonts files for tesstrain."
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--lang", metavar="LANG",
                      help="Single language code (e.g. eng)")
    mode.add_argument("--all", action="store_true",
                      help="Process all languages discovered in tessdata/")

    parser.add_argument("--output", type=Path, default=None,
                        help="Output file path (single-lang mode, stdout if omitted)")
    parser.add_argument("--output-dir", type=Path, default=default_out,
                        metavar="DIR",
                        help="Output directory for --all mode (default: training/generated/)")

    args = parser.parse_args()

    char_groups = parse_characters(config_dir / "characters.txt")

    if args.lang:
        # Single language — write to stdout or a file
        chars = get_chars_for_lang(args.lang, char_groups)
        lines = build_training_lines(args.lang, chars)
        text = "\n".join(lines) + "\n"

        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
            print(f"Wrote {len(lines)} lines to {args.output}")
        else:
            sys.stdout.write(text)

    else:
        # All languages
        languages = get_languages_from_tessdata(tessdata_dir)
        if not languages:
            print("ERROR: no .traineddata files found in tessdata/", file=sys.stderr)
            sys.exit(1)

        print(f"Processing {len(languages)} languages -> {args.output_dir}")
        print()

        for lang in languages:
            chars = get_chars_for_lang(lang, char_groups)
            txt_path = write_training_text(lang, chars, args.output_dir)
            fnt_path = write_fonts_file(lang, args.output_dir)
            line_count = txt_path.read_text(encoding="utf-8").count("\n")
            print(f"  {lang:<16} {len(chars):>4} chars   {line_count:>5} lines   "
                  f"fonts: {', '.join(get_fonts_for_lang(lang))}")

        print()
        print(f"Done. Output in {args.output_dir}")


if __name__ == "__main__":
    main()
