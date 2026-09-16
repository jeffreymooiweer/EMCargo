"""The catalogue search always spoke Dutch.

`search_catalog` had no language parameter at all: the commodity names came out
invariably as `labels["nl"]`. That hit an English user just as hard as a German
one — the screen in English, the suggestions in Dutch.

It is not a cosmetic point. The suggestion the user clicks becomes the
description in the goods column of their waybill; what comes out here ends up on
a CMR.

The searching itself keeps going across all languages — whoever types "Stahl"
while reading Dutch should simply find steel. Only what is returned follows the
language.
"""

import pytest

from app.core.database import Base, SessionLocal, engine
from app.core.startup import seed_catalogs
from app.core.languages import SUPPORTED
from app.services.catalog_search import (
    MATERIAL_LABELS,
    PRODUCT_LABELS,
    material_label,
    product_label,
    search_catalog,
)


@pytest.fixture(scope="module")
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    seed_catalogs(session)
    yield session
    session.close()


def labels(db, query, language):
    return [hit["label"] for hit in search_catalog(db, query, limit=5, language=language)]


@pytest.mark.parametrize("language,expected", [
    ("nl", "Staal"),
    ("en", "Steel"),
    ("de", "Stahl"),
])
def test_a_material_comes_back_in_the_language_you_asked_for(db, language, expected):
    assert expected in labels(db, "staal", language)


@pytest.mark.parametrize("query", ["staal", "steel", "Stahl"])
def test_the_search_itself_keeps_understanding_every_language(db, query):
    """Whoever reads German but pastes a Dutch item list still has to find their
    material."""
    assert "Stahl" in labels(db, query, "de")


def test_a_german_name_that_exists_only_as_a_label_is_findable(db):
    """The German names are in the seed as a label, not as an alias. If the
    search looked only at aliases, the user would not find the term that is on
    their own screen."""
    assert "Edelstahl" in labels(db, "Edelstahl", "de")
    assert "Quecksilber" in labels(db, "Quecksilber", "de")


def test_a_template_suggestion_follows_the_language_too(db):
    """The template suggestion ("hoekprofiel 80x80x8x6000") is precisely the text
    that ends up on the document unchanged."""
    assert any("Winkelprofil" in label for label in labels(db, "Winkelprofil", "de"))
    assert any("Hoekprofiel" in label for label in labels(db, "hoekprofiel", "nl"))
    assert any("Angle Profile" in label for label in labels(db, "hoekprofiel", "en"))


@pytest.mark.parametrize("language", SUPPORTED)
def test_profile_suggestions_show_actual_density_without_dimension_prompt(db, language):
    """The mobile dropdown must show the material density just like ordinary
    goods. A made-up example size distracted from selection and looked required.
    A shape without a known material has no density to invent.
    """
    hits = search_catalog(db, "staal hoekprofiel", limit=25, language=language)
    templates = [hit for hit in hits if hit["source"] == "template"]
    assert templates
    assert any(hit["sublabel"] == "7850 kg/m³" for hit in templates)
    assert all("kg/m³" in hit["sublabel"] for hit in templates if hit["sublabel"])
    bare = search_catalog(db, "hoekprofiel", limit=5, language=language)
    assert next(hit for hit in bare if hit["source"] == "template")["sublabel"] is None


def test_an_unknown_language_falls_back_rather_than_returning_nothing(db):
    """A label must never be empty; then there would be nothing in the goods
    column."""
    assert all(hit["label"] for hit in search_catalog(db, "staal", limit=5, language="fr"))


# --- De labeltabellen -----------------------------------------------------


def test_every_product_type_speaks_every_language():
    """Growing with SUPPORTED instead of naming three languages.

    These two tests literally required {"nl", "en", "de"}. When French arrived
    they failed not because something was missing, but because something had been
    added — a guard that sees a new language as an error does not guard that
    language.
    """
    for product_type, names in PRODUCT_LABELS.items():
        assert set(names) == set(SUPPORTED), product_type
        assert all(names.values()), product_type


def test_every_fallback_material_speaks_every_language():
    for name, names in MATERIAL_LABELS.items():
        assert set(names) == set(SUPPORTED), name
        assert all(names.values()), name


def test_product_label_never_returns_an_internal_key():
    assert product_label("angle_profile", "de") == "Winkelprofil"
    # A type the table does not know must not put "angle_profile" on the screen.
    assert product_label("mystery_type", "de") == "mystery type"


def test_material_label_prefers_the_database_over_the_fallback_table(db):
    from app.models.user import Material

    steel = db.query(Material).filter(Material.canonical_name == "steel").one()
    assert material_label(steel, "de") == "Stahl"
