"""An extra language has to be complete, or it is misleading.

The danger of one more language is not in what goes wrong but in what quietly
looks right: a missing translation falls back to another language, the screen
keeps working, and the user sees a French form with Dutch field names without
noticing anything is missing. On a transport document that is not a cosmetic
problem — a consignor who does not read "Verpakkingsgroep" does not fill it in.

These tests therefore run over the data files themselves: every block carrying a
Dutch *and* an English text has to carry one in every other language the
application claims to speak. That way a new text lands in every language at once
or it does not land.

**These tests name no language at all.** They read `SUPPORTED` from
`app.core.languages` and require every language in it except `nl` and `en`, which
are the source languages. Until v1.44.0 there was a literal `"de"` everywhere,
so when French arrived they did not guard French — adding a language then meant
extending the guard as well, and that is exactly what you forget. Now `SUPPORTED`
is the only place a language is switched on.
"""

import ast
import json
from pathlib import Path

import pytest

from app.core.languages import DEFAULT, SUPPORTED, normalise, pick
from app.services.parser.language_detector import detect_language
from app.services.parser.product_detector import detect_product_type

ROOT = Path(__file__).resolve().parents[1]

# The files from which text goes to the screen and to the documents.
TRANSLATED_FILES = [
    "app/config/dg_instructions.json",
    "app/config/dg_compliance.json",
    "app/config/document_registry.json",
    "seed/dg/ems.json",
    "seed/dg/packagings.json",
    "seed/dg/segregation_groups.json",
    "seed/dg/imdg_42_24.json",
    # The goods database: the name the user clicks becomes the description on
    # their waybill.
    "seed/materials.json",
    "seed/reference_items.json",
    "seed/container_templates.json",
]

# Some blocks carry their languages as a suffix: note_nl/note_en.
SUFFIXES = ("note", "items", "changes", "assigned_to_note")

#: The languages that are guarded: everything the application speaks, except the
#: two source languages. Grows with `SUPPORTED` by itself.
EXTRA_LANGUAGES = tuple(language for language in SUPPORTED if language not in ("nl", "en"))


def translated_blocks(value, language, path=""):
    """Every block with a Dutch *and* an English text, with its path."""
    if isinstance(value, dict):
        if "nl" in value and "en" in value:
            yield path or ".", value, language
        for suffix in SUFFIXES:
            if f"{suffix}_nl" in value and f"{suffix}_en" in value:
                yield f"{path}#{suffix}", value, f"{suffix}_{language}"
        for key, item in value.items():
            yield from translated_blocks(item, language, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from translated_blocks(item, language, f"{path}[{index}]")


def source_key(block_key, language):
    """`de` goes with `en`; `note_de` goes with `note_en`."""
    return "en" if block_key == language else f"{block_key[: -len(language)]}en"


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("language", EXTRA_LANGUAGES)
@pytest.mark.parametrize("name", TRANSLATED_FILES)
def test_every_translated_text_carries_each_extra_language(name, language):
    incomplete = [path for path, block, key in translated_blocks(load(name), language)
                  if not block.get(key)]
    assert incomplete == [], f"{name}: geen {language} voor {incomplete[:5]}"


@pytest.mark.parametrize("language", EXTRA_LANGUAGES)
@pytest.mark.parametrize("name", TRANSLATED_FILES)
def test_a_translation_keeps_the_shape_of_the_other_languages(name, language):
    """A list stays a list, and the same length.

    The fixed texts of a form and the exemption provisions of 1.1.3.6 are lists;
    a translation that turns those into one line produces a document with four
    missing provisions.
    """
    wrong = []
    for path, block, key in translated_blocks(load(name), language):
        english, translated = block[source_key(key, language)], block[key]
        if type(translated) is not type(english):
            wrong.append(f"{path}: {type(translated).__name__} vs {type(english).__name__}")
        elif isinstance(english, list) and len(translated) != len(english):
            wrong.append(f"{path}: {len(translated)} regels vs {len(english)}")
    assert wrong == []


@pytest.mark.parametrize("language", EXTRA_LANGUAGES)
def test_a_translation_is_not_simply_the_dutch_text(language):
    """A 'translation' that repeats the Dutch text is not a translation.

    Technical terms that stay untranslated everywhere are the exception —
    "Proper Shipping Name", "Verified Gross Mass", the IATA warning that has to
    be printed verbatim. Those are recognisable because Dutch and English were
    already identical; what was *not* identical there is a sentence that ought to
    be translated.
    """
    copies = []
    for name in TRANSLATED_FILES:
        for path, block, key in translated_blocks(load(name), language):
            source = source_key(key, language)
            dutch = block[f"{source[:-2]}nl"]
            english = block[source]
            if not isinstance(dutch, str) or len(dutch.split()) <= 3:
                continue
            # A difference in capitals alone does not count as a translation:
            # "Air Waybill Shipping Instructions" is the same term in every
            # language.
            if dutch.casefold() != english.casefold() and block[key] == dutch:
                copies.append(f"{name}{path}")
    assert copies == []


# --- The texts that live in the code itself --------------------------------


def bilingual_literals(tree):
    """Every dict literal in the source with an 'nl' *and* an 'en' key."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        keys = {k.value for k in node.keys
                if isinstance(k, ast.Constant) and isinstance(k.value, str)}
        if {"nl", "en"} <= keys:
            yield node.lineno, keys


@pytest.mark.parametrize("language", EXTRA_LANGUAGES)
def test_no_translation_left_behind_in_the_code(language):
    """Half the texts are not in a data file but in the code: the fixed texts of
    the exporter, the segregation wordings, the product names. Those are just as
    easy to forget when a language is added, and there of all places it does not
    show — a two-way choice then serves up the wrong language without complaint.
    """
    missing = []
    for path in sorted((ROOT / "app").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for lineno, keys in bilingual_literals(tree):
            if language not in keys:
                missing.append(f"{path.relative_to(ROOT)}:{lineno}")
    assert missing == []


def test_nothing_decides_between_two_languages_any_more():
    """`"en" if language.startswith("en") else "nl"` was the old way. Such a
    branch silently gives a third language the wrong answer; it should have been
    replaced by `normalise()` and `pick()`."""
    offenders = []
    for path in sorted((ROOT / "app").rglob("*.py")):
        if path.name == "languages.py":
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if 'lang == "nl"' in line or 'language == "nl"' in line or 'startswith("en")' in line:
                offenders.append(f"{path.relative_to(ROOT)}:{number}")
    assert offenders == []


# --- The choice itself -----------------------------------------------------


def test_the_frontend_offers_the_same_languages():
    """German on the screen and Dutch in the export is worse than Dutch alone:
    the user then thinks they are getting a German document."""
    source = (ROOT.parent / "frontend/src/i18n/language.ts").read_text(encoding="utf-8")
    line = next(line for line in source.splitlines() if "SUPPORTED_LANGUAGES" in line)
    assert all(f'"{lang}"' in line for lang in SUPPORTED), line


@pytest.mark.parametrize("given,expected", [
    ("de", "de"), ("DE", "de"), ("de-AT", "de"), ("de_DE", "de"),
    ("en", "en"), ("en-GB", "en"), ("nl", "nl"),
    # French has belonged to SUPPORTED since v1.44.0 and therefore no longer
    # falls back to the default language. This line was here as proof that an
    # unknown language was caught properly; "it" now takes that role.
    ("fr", "fr"), ("fr-BE", "fr"), ("FR_CH", "fr"),
    ("it", DEFAULT), ("", DEFAULT), (None, DEFAULT), (123, DEFAULT),
])
def test_a_language_code_is_narrowed_to_one_we_speak(given, expected):
    assert normalise(given) == expected


def test_a_missing_translation_falls_back_instead_of_showing_nothing():
    """A user can still read a field name in another language; a field without a
    name they cannot."""
    assert pick({"nl": "Afzender", "en": "Consignor"}, "de") == "Consignor"
    assert pick({"nl": "Afzender"}, "en") == "Afzender"
    assert pick({"de": "Absender"}, "de") == "Absender"


def test_an_empty_translation_counts_as_missing():
    # An empty string in the registry would otherwise produce an empty label.
    assert pick({"nl": "Afzender", "en": "", "de": ""}, "de") == "Afzender"


# --- The language of what the user pastes -----------------------------------


@pytest.mark.parametrize("text,expected", [
    ("Stalen hoekprofiel 80x80x8x6000", "nl"),
    ("Steel angle profile 80x80x8x6000", "en"),
    ("Stahl Winkelprofil 80x80x8x6000, 8 Stück", "de"),
    ("Träger HEA200, Länge 6000", "de"),
])
def test_a_pasted_line_gets_its_answer_in_its_own_language(text, expected):
    """The derived description comes back in the language of the input; whoever
    pasted German used to get English back."""
    assert detect_language(text) == expected


@pytest.mark.parametrize("text", ["", "artikel 12345", None])
def test_without_a_clue_the_paste_counts_as_dutch(text):
    assert detect_language(text) == DEFAULT


@pytest.mark.parametrize("text,expected", [
    ("Stahl Winkelprofil 80x80x8x6000", "angle_profile"),
    ("Quadratrohr 60x60x3", "square_tube"),
    ("Stahlrohr 42,4x2,6", "round_tube"),
    ("Rundstab 20 mm", "round_bar"),
    ("Stahlblech 2000x1000x5", "plate"),
    ("Träger HEA200 6000", "beam"),
    ("Betonplatte 2000x1000", "concrete_slab"),
    ("Sperrholz 18 mm", "plywood"),
    ("PVC-Rohr 110 mm", "pvc_pipe"),
    ("Kunststoffplatte 3 mm", "plastic_sheet"),
])
def test_a_german_description_is_recognised_as_a_product(text, expected):
    """The language of the screen does not help when the input is not recognised:
    an unrecognised product yields no weight and therefore no usable document."""
    assert detect_product_type(text) == expected


def test_a_german_plastic_pipe_is_not_mistaken_for_a_steel_one():
    """A bare 'Rohr' would swallow a PVC pipe as well, and that weighs an order
    of magnitude less."""
    assert detect_product_type("PVC-Rohr 110 mm") == "pvc_pipe"
    assert detect_product_type("Kunststoffrohr 110 mm") == "pvc_pipe"


def test_a_word_that_two_languages_share_does_not_decide():
    """'verzinkt' and 'beton' are in the Dutch *and* the German list. A line
    carrying only such a word must not tip over into German."""
    assert detect_language("beton verzinkt") == "nl"
    assert detect_language("Blech beton verzinkt") == "de"  # 'Blech' geeft de doorslag


def test_something_that_is_not_a_translation_block_yields_the_default():
    assert pick(None, "de") == ""
    assert pick("Absender", "de", "-") == "-"
    assert pick({}, "de", "-") == "-"
