"""A density is useful only when its source state survives import and use.

The previous catalogue had no row-level provenance. This expansion must not
turn basic wood density or back-converted numbers into shipment mass, pool
different moisture states, lose sources on upgrade, or certify a local edit.
"""
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.startup import seed_catalogs
from app.models.user import Material
from app.services.catalog_sync.materials import load_seed_material_records, upsert_materials
from app.services.catalog_search import search_catalog
from app.services.density_references import density_reference, list_density_references
from app.services.pipeline import match_material, parse_and_calculate

SEED = Path(__file__).resolve().parents[1] / "seed"
REFERENCES = [row for path in sorted(SEED.glob("materials_measured*.json"))
              for row in json.loads(path.read_text(encoding="utf-8"))]


@pytest.fixture(scope="module")
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_catalogs(session)
        yield session
    engine.dispose()


def test_every_wood_value_reconciles_to_original_measurements_at_one_moisture():
    """Check all source records, not just a few convenient examples."""
    groups = defaultdict(list)
    with (SEED / "density_sources" / "gwdd_original_measurements.csv").open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            assert row["backtransformed"] == "0"
            assert row["quantity_reference"] in {"Airdry SG/Density", "Ovendry SG/Density"}
            assert row["source_long"]
            groups[row["canonical_name"]].append(row)
    for reference in REFERENCES:
        provenance = reference["provenance"]
        if provenance["kind"] != "measurement_mean":
            continue
        rows = groups.pop(reference["canonical_name"])
        densities = [float(row["value_reference"]) * 1000 for row in rows]
        assert reference["density_kg_m3"] == round(mean(densities), 1)
        assert reference["density_min_kg_m3"] == round(min(densities), 1)
        assert reference["density_max_kg_m3"] == round(max(densities), 1)
        assert provenance["source_record_ids"] == [row["id"] for row in rows]
        assert len({row["moisture_airdry"] for row in rows}) == 1
        assert len({row["species"] for row in rows}) == 1
    assert not groups


def test_source_entries_have_unique_qualified_names_and_complete_languages():
    from app.core.languages import SUPPORTED

    assert len(REFERENCES) >= 11000
    names = [record.canonical_name for record in load_seed_material_records(SEED / "materials.json")]
    assert len(names) == len(set(names))
    for row in REFERENCES:
        assert row["density_kg_m3"] > 0
        assert set(row["language_labels"]) == set(SUPPORTED)
        assert row["provenance"]["source_url"].startswith("https://")
        assert row["provenance"]["source_record_ids"]
        assert row["aliases"] == []  # Never silently assume moisture for a bare species name.


def test_conflicting_bulk_rows_are_not_imported_and_units_reconcile():
    references = {row["provenance"]["source_record_ids"][0]: row for row in REFERENCES if row["provenance"]["kind"] == "published_reference"}
    assert "41" not in references  # 50 lb/ft3 versus 0.004 g/cm3 in the original table.
    with (SEED / "density_sources" / "hapman_bulk.csv").open(encoding="utf-8") as file:
        for row in csv.DictReader(file):
            converted = float(row["lb_ft3"]) * 0.45359237 / 0.3048 ** 3
            assert references[row["source_record_id"]]["density_kg_m3"] == round(converted, 1)
            assert abs(float(row["g_cm3"]) * 1000 - converted) <= max(5.1, converted * 0.015)


def test_offline_upgrade_adds_missing_rows_without_overwriting_local_edits(db):
    original = db.query(Material).filter_by(canonical_name="gwdd_abies_alba_wood_mc12").one()
    old_density, old_active = original.density_kg_m3, original.active
    original.density_kg_m3 = 999
    original.active = False
    try:
        seed_catalogs(db)
        assert original.density_kg_m3 == 999 and not original.active
        assert density_reference(original)["kind"] == "unverified"
        assert db.query(Material).count() >= 12893
        assert upsert_materials(db, load_seed_material_records(SEED / "materials.json"), only_missing=True) == (0, 0)
    finally:
        original.density_kg_m3, original.active = old_density, old_active
        db.commit()


def test_selected_wood_condition_uses_solid_density_without_a_hidden_stacking_factor(db):
    item = db.query(Material).filter_by(canonical_name="gwdd_abies_alba_wood_mc12").one()
    label = json.loads(item.language_labels_json)["nl"]
    result = parse_and_calculate(f"{label} | 2 | m3", db=db)["lines"][0]
    assert result["material"] == item.canonical_name
    assert result["weight_total_kg"] == pytest.approx(2 * item.density_kg_m3)
    assert result["density_reference"]["condition_key"] == "wood_mc_12"
    assert match_material("Abies alba", db)[0] is not item


def test_bulk_calculation_discloses_the_reference_estimate(db):
    item = db.query(Material).filter_by(canonical_name="hapman_acetaminophen_powder_unmilled").one()
    label = json.loads(item.language_labels_json)["nl"]
    result = parse_and_calculate(f"{label} | 2 | m3", db=db)["lines"][0]
    assert result["weight_total_kg"] == pytest.approx(2 * item.density_kg_m3)
    assert result["status"] == "needs_review"
    assert "density_reference_estimate" in result["messages"]
    assert result["density_reference"]["kind"] == "published_reference"


@pytest.mark.parametrize("language", ["nl", "en", "de", "fr"])
def test_qualified_wood_is_still_found_and_calculated_in_every_language(db, language):
    item = db.query(Material).filter_by(canonical_name="gwdd_abies_alba_wood_mc12").one()
    label = json.loads(item.language_labels_json)[language]
    assert match_material(label, db)[0] is item
    assert any(hit["label"] == label for hit in search_catalog(db, label, language=language))


def test_search_is_bounded_and_treats_moisture_percent_as_literal(db):
    page = list_density_references(db, "Abies alba 12%", limit=1)
    assert page["total"] == 1
    assert page["results"][0]["condition_key"] == "wood_mc_12"
    assert len(list_density_references(db, "", limit=3)["results"]) == 3
    assert list_density_references(db, "does-not-exist %_")["total"] == 0


def test_every_nist_value_keeps_the_original_point_identity_phase_and_conditions():
    source_rows = json.loads((SEED / "density_sources" / "nist_measurements.json").read_text())
    references = {r["canonical_name"]: r for r in REFERENCES if r["source"].startswith("seed:nist:")}
    assert len(references) > 1900
    identities = set()
    for row in source_rows:
        identity = row["compound"]["sStandardInChIKey"]
        key = f"nist_{identity.lower()}_{row['phase'].lower()}"
        reference = references.pop(key)
        value = row["point"]["PropertyValue"][0]
        assert reference["density_kg_m3"] == value["nPropValue"]
        provenance = reference["provenance"]
        assert provenance["kind"] == "measurement"
        assert provenance["chemical_identity"] == identity
        assert provenance["temperature_c"] == pytest.approx(row["temperature_k"] - 273.15)
        assert provenance["pressure_kpa"] == row["pressure_kpa"]
        assert 80 <= row["pressure_kpa"] <= 120
        assert provenance["basis"] == ("liquid" if row["phase"] == "Liquid" else "solid")
        assert row["property"]["ePresentation"] == "Direct value, X"
        assert not any(word in provenance["method"].lower() for word in ("calculat", "estimat", "derived", "diffraction", "x-ray"))
        identities.add(identity)
    assert not references and len(identities) > 1900


def test_all_industrial_and_food_values_reconcile_without_filling_missing_values():
    facts = json.loads((SEED / "density_sources" / "industrial_food_facts.json").read_text())
    references = {r["canonical_name"]: r for r in REFERENCES}
    conversions = {"kg/m3": 1, "g/cm3": 1000, "g/ml": 1000, "lb/in3": 0.45359237 / 0.0254 ** 3}
    categories = set()
    for row in facts:
        reference = references[row["canonical_name"]]
        assert reference["density_kg_m3"] == round(row["original_value"] * conversions[row["original_unit"]], 6)
        assert reference["provenance"]["source_record_ids"] == row["source_record_ids"]
        if row["canonical_name"].startswith("campus_"):
            assert row["method"] == "ISO 1183"
            values = row["source_row"]["Spt-578"].split("/")
            index = 1 if row["condition_key"] == "campus_conditioned" else 0
            assert float(values[index].strip()) == row["original_value"]
            if len(values) == 2:
                assert row["condition_key"] in {"campus_dry", "campus_conditioned"}
        if row["canonical_name"].startswith("fao_"):
            cells = row["source_row"]["cells"]
            assert float(cells[1]) == row["original_value"]  # Density, not adjacent specific gravity.
            assert cells[3] not in {"ASI", "TB", "CG", "CSG", "UK 6th"}
        categories.add(row["category"])
    assert {"metal", "plastic", "food", "insulation"} <= categories


def test_category_filter_reaches_food_and_polymers_without_wood_results(db):
    for category in ("plastic", "food", "metal", "chemical", "insulation"):
        page = list_density_references(db, "", category=category, limit=4)
        assert page["total"] > 0
        for row in page["results"]:
            item = db.query(Material).filter_by(canonical_name=row["canonical_name"]).one()
            assert item.category == category


@pytest.mark.parametrize("phase", ["Liquid", "Crystal"])
def test_chemical_measurements_use_source_phase_and_density_in_calculation(db, phase):
    row = next(r for r in REFERENCES if r["source"].startswith("seed:nist:")
               and r["provenance"]["phase"] == phase.lower())
    item = db.query(Material).filter_by(canonical_name=row["canonical_name"]).one()
    # Temperatures and chemical locants must not become shipment dimensions.
    label = json.loads(item.language_labels_json)["nl"]
    result = parse_and_calculate(f"{label} | 2 | m3", db=db)["lines"][0]
    assert result["material"] == item.canonical_name
    assert result["weight_total_kg"] == pytest.approx(2 * item.density_kg_m3)
    assert result["calculation_method"] == "unit_" + row["provenance"]["basis"]
    assert result["density_reference"]["temperature_c"] == row["provenance"]["temperature_c"]
