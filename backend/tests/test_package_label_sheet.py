"""The package label sheet: the right content at the right size, and honest
about the two things it will not do.

The size assertions here are not decoration. A label built to the other reading
of "100 mm x 100 mm" is 71 mm on a side where the regulation asks for 100, on
every package, and it looks entirely correct. So the printed geometry is
measured out of the produced PDF rather than trusted.
"""
import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_current_user
from app.main import app
from app.services.dg import database
from app.services.documents.package_label_sheet import (
    FULL_SIZE_MM,
    artwork_for,
    render_package_label_sheet,
)

CONSIGNMENT = {"reference": "CP-2026-500", "consignor_name": "Afzender BV"}


def goods(un, **extra):
    rows = database.get_un_entries(un)
    row = rows[0] if rows else {}
    item = {
        "un_number": un,
        "proper_shipping_name": row.get("name_nl") or "",
        "class": row.get("class") or "",
        "labels": row.get("labels") or "",
        "packing_group": row.get("packing_group") or "",
    }
    item.update(extra)
    return item


def sheet(*products, profiles=("ADR",), language="nl"):
    entries = [{"line_id": "1", "products": list(products)}]
    return render_package_label_sheet(
        CONSIGNMENT, [], entries, language, list(profiles))


#: The brand's logo sits in every page header since v1.178.0, never wider
#: than 46 mm. Artwork is what is printed at label size, so anything narrower
#: than this is not artwork.
ARTWORK_MIN_MM = 50


def artwork_rects(page):
    """Where the labels and marks are on a page, the header logo left out."""
    return [rect for image in page.get_images(full=True)
            for rect in page.get_image_rects(image[0])
            if rect.width / 72 * 25.4 >= ARTWORK_MIN_MM]


def pages(path):
    with pymupdf.open(str(path)) as document:
        return [page.get_text() for page in document]


def artwork_pages(path):
    """The pages carrying a figure someone is meant to cut out and apply.

    Detected by the figure rather than by position, so the test does not quietly
    stop covering a page when the working page grows onto a second sheet.
    """
    with pymupdf.open(str(path)) as document:
        return [page.get_text() for page in document if artwork_rects(page)]


# --- the size, measured off the page ---


def test_a_label_is_printed_at_one_hundred_millimetres_on_each_side():
    """5.2.2.2.1.1.2, read as 49 CFR 172.407(c)(1) spells it out.

    The artwork is the diamond's bounding box — its points touch the canvas
    edges — so a box of 141.42 mm gives a side of exactly 100 mm. Measured out
    of the PDF because an off-by-root-two here is invisible on screen and wrong
    on every package.
    """
    path = sheet(goods("1263"))
    with pymupdf.open(str(path)) as document:
        page = document[1]
        rects = artwork_rects(page)
    assert rects, "the label page carries no artwork"
    width_mm = rects[0].width / 72 * 25.4
    assert round(width_mm, 1) == round(FULL_SIZE_MM, 1)
    assert round(width_mm / 2 ** 0.5) == 100


def test_the_page_is_a4_and_carries_cut_marks():
    path = sheet(goods("1263"))
    with pymupdf.open(str(path)) as document:
        page = document[1]
        assert round(page.rect.width / 72 * 25.4) == 210
        assert round(page.rect.height / 72 * 25.4) == 297
        drawn = sum(len(item["items"]) for item in page.get_drawings())
    # Two strokes at each of four corners.
    assert drawn >= 8


def test_one_label_per_page_and_the_arithmetic_that_says_so():
    """Two full-size labels need 283 mm, against A4's 210 by 297.

    Side by side is impossible. Stacked is not impossible — 282.84 mm does fit
    inside 297 mm — and the first version of this test claimed otherwise, which
    is why the claim is now written as arithmetic rather than as a verdict.
    What rules it out is what is left: 14 mm for both margins, the caption and
    the cut marks together.
    """
    two = FULL_SIZE_MM * 2
    assert two > 210, "side by side does not fit across the page"
    assert two < 297, "stacked fits on the paper; margins are what rule it out"
    assert round(297 - two) == 14


# --- which artwork answers for which model ---


@pytest.mark.parametrize("model,expected", [
    ("3", "3.png"),
    ("6.1", "6_1.png"),
    ("9A", "9A.png"),
    ("2.1", "2_1.png"),
])
def test_a_model_maps_to_its_own_artwork(model, expected):
    found = artwork_for(model)
    assert found is not None and found.name == expected


@pytest.mark.parametrize("division", ["1.1D", "1.2B", "1.3C"])
def test_divisions_one_one_to_one_three_share_model_one(division):
    """The regulation prints one model for those three, with a place on it for
    the division and the compatibility group."""
    found = artwork_for(division)
    assert found is not None and found.name == "1.png"


@pytest.mark.parametrize("division,expected", [
    ("1.4S", "1_4.png"), ("1.5D", "1_5.png"), ("1.6N", "1_6.png")])
def test_divisions_one_four_to_one_six_have_their_own_models(division, expected):
    found = artwork_for(division)
    assert found is not None and found.name == expected


def test_an_unknown_model_gets_nothing_rather_than_a_neighbour():
    """Substituting a nearby model would print the wrong hazard. Printing
    nothing leaves the label named on the working page and not drawn."""
    assert artwork_for("42") is None
    assert artwork_for("") is None


# --- what the sheet says, and what it refuses to say ---


def test_the_working_page_lists_the_regime_beside_every_line():
    """A consignment going by road and then by sea gets both answers, because
    they differ, and a packer who sees only one packs the wrong box."""
    text = pages(sheet(goods("1263"), profiles=("ADR", "IMDG")))[0]
    assert "ADR" in text and "IMDG" in text


def test_the_sea_leg_shows_the_name_the_land_leg_does_not():
    """IMDG 5.2.1.1 marks the proper shipping name on every package; ADR asks
    for it on Class 1 and Class 7 only. Paint is neither."""
    text = pages(sheet(goods("1263"), profiles=("ADR", "IMDG")))[0]
    assert "shipping name" in text.replace("\n", " ")


def test_the_sheet_says_paper_is_not_the_material():
    """5.2.1.2 wants a mark that survives the weather, and the IMDG Code one
    that survives three months in the sea. Neither is a laser print, and a
    sheet that stays quiet about that invites exactly that mistake."""
    text = pages(sheet(goods("1263")))[0].replace("\n", " ")
    assert "drie maanden" in text or "three months" in text


def test_the_material_warning_is_on_every_page_that_gets_cut_up():
    """The material is chosen at the printer, not on the working page.

    The full note lives on the working page, which may never be printed at all;
    the page in hand when the stock is loaded is the artwork page. Until
    v1.163.1 that page said nothing about the material.

    Asserted on the name of the standard, which is the same in all four
    languages, and on the figure rather than the page number, so a working page
    that grows onto a second sheet cannot silently narrow what is covered.
    """
    for language in ("nl", "en", "de", "fr"):
        body = artwork_pages(sheet(
            goods("1263"), goods("3480"),
            profiles=("ADR", "IMDG"), language=language))
        assert body, f"no artwork pages in {language}"
        for number, text in enumerate(body, start=1):
            assert "BS 5609" in text.replace("\n", " "), (
                f"artwork page {number} in {language} carries a figure "
                f"without the material warning")


def test_the_orientation_arrows_are_named_as_not_assessed():
    text = pages(sheet(goods("1263")))[0].replace("\n", " ")
    assert "5.2.1.10" in text


# --- the marks, now that their figures are measured ---


def test_the_battery_mark_is_drawn_and_carries_the_un_number():
    """The figure prints an asterisk where the number goes. An asterisk is a
    footnote in a book; on a package it is a mark that says nothing, and which
    cells are inside is the only thing this mark exists to say."""
    body = pages(sheet(goods("3480")))
    page = next(text for text in body if "5.2.1.9.2" in text)
    assert "UN 3480" in page.replace("\n", " ")


def test_the_battery_mark_is_a_hundred_millimetre_square():
    """5.2.1.9.2 in as many words: 100 mm by 100 mm, hatched edging at least
    5 mm. Measured off the page, because the frame is built from those numbers
    and a typo in them would look like a mark."""
    path = sheet(goods("3480"))
    with pymupdf.open(str(path)) as document:
        page = next(page for page in document if "5.2.1.9.2" in page.get_text())
        squares = [item[1] for drawing in page.get_drawings()
                   for item in drawing["items"] if item[0] == "re"]
        widths = sorted({round(rect.width / 72 * 25.4) for rect in squares})
    assert 100 in widths, "the mark itself is not 100 mm across"
    assert 90 in widths, "5 mm of hatching on each side leaves 90 mm inside"


def test_the_battery_mark_needs_its_symbol_and_will_not_fake_one(monkeypatch):
    """A frame with a number in it and an empty middle is not a smaller version
    of this mark. It is a different one, and what makes it recognised across a
    warehouse is the picture."""
    from app.services.documents import package_label_sheet as module

    monkeypatch.setattr(module, "LABELS", module.LABELS.parent / "absent")
    assert not any("5.2.1.9.2" in text for text in pages(sheet(goods("3480"))))


def test_the_orientation_arrows_are_printed_with_their_conditions():
    """5.2.1.10.1 gives them no size, so the caption has to say that the size
    on the page is this sheet's choice — and 5.2.1.10.3 forbids arrows put
    there for any other reason, which a packer holding the page should read
    before cutting."""
    page = next(text for text in pages(sheet(goods("1263")))
                if "5.2.1.10.1" in text)
    flat = page.replace("\n", " ")
    assert "5.2.1.10.2" in flat and "5.2.1.10.3" in flat


def test_the_environmentally_hazardous_mark_is_printed_at_label_size():
    """5.2.1.8.3 words its minimum exactly as 5.2.2.2.1.1.2 words a label's, and
    the two figures are drawn at the same scale in the edition. So the mark
    takes the same reading: 100 mm on a side, 141 mm from point to point."""
    path = sheet(goods("3082", environmentally_hazardous="P"))
    with pymupdf.open(str(path)) as document:
        # The working page names 5.2.1.8 in its marks column too, so the page
        # wanted here is the one that both names the provision and draws it.
        page = next(page for page in document
                    if "5.2.1.8" in page.get_text() and artwork_rects(page))
        rects = artwork_rects(page)
    assert rects
    assert round(min(rects[0].width, rects[0].height) / 72 * 25.4, 1) \
        >= round(FULL_SIZE_MM, 1)


def test_no_artwork_is_ever_printed_below_its_own_minimum():
    """The files are trimmed to their ink and are not all exactly square. Fitting
    such an image inside a 141.42 mm box puts the other direction under it, and
    "minimum dimensions" is the one thing this number means."""
    path = sheet(goods("3082", environmentally_hazardous="P"), goods("1263"))
    with pymupdf.open(str(path)) as document:
        for page in document:
            for rect in artwork_rects(page):
                if round(rect.width / 72 * 25.4) < 100:
                    continue  # the battery symbol lives inside its frame
                assert round(min(rect.width, rect.height) / 72 * 25.4, 1) \
                    >= round(FULL_SIZE_MM, 1)


def test_a_consignment_without_dangerous_goods_says_so_on_one_page():
    path = render_package_label_sheet(CONSIGNMENT, [], [], "nl", ["ADR"])
    body = pages(path)
    assert len(body) == 1
    assert "geen gevaarlijke goederen" in body[0].replace("\n", " ")


def test_the_same_label_is_not_printed_twice_for_one_line():
    """Two products on one line that carry the same model get one page."""
    body = pages(sheet(goods("1263"), goods("1263")))
    assert sum(1 for text in body if "Model 3" in text) == 1


def test_every_language_renders():
    for language in ("nl", "en", "de", "fr"):
        body = pages(sheet(goods("1263"), language=language))
        assert len(body) >= 2
        assert body[0].strip()


# --- through the route a wizard actually calls ---


def user():
    from types import SimpleNamespace
    return SimpleNamespace(id=1, username="verify", role="admin", active=True)


def test_the_export_route_produces_the_sheet():
    app.dependency_overrides[get_current_user] = user
    with TestClient(app) as api:
        response = api.post("/api/documents/export", json={
            "document_key": "package_label_sheet",
            "values": CONSIGNMENT,
            "lines": [],
            "dangerous_goods": [{"line_id": "1", "products": [goods("1263", marine_pollutant="N",
                imdg_source_reference="Synthetic test assessment, IMDG 42-24", imdg_source_reviewed="Y")]}],
            "output_language": "nl",
            "profiles": ["ADR", "IMDG"],
        })
    app.dependency_overrides.pop(get_current_user, None)
    assert response.status_code == 200, response.text
    assert response.content[:4] == b"%PDF"


def test_the_registry_offers_it_on_every_mode_that_carries_packages():
    """Air is out: the IATA marking rules have not been read."""
    from app.services.documents.registry import get_registry
    registry = get_registry()
    per_mode = {mode["key"]: mode["documents"] for mode in registry["modalities"]}
    for mode in ("road", "rail", "sea", "inland"):
        assert "package_label_sheet" in per_mode[mode]
    assert "package_label_sheet" not in per_mode["air"]


# --- the limited quantities mark, which is drawn rather than cut ---


def limited_quantities_sheet(language="nl"):
    product = {
        "un_number": "1263", "proper_shipping_name": "VERF", "class": "3",
        "labels": "3", "packing_group": "II", "limited_quantity": "5 L",
        "net_per_inner_packaging": "1 L", "gross_mass_per_package": "10 kg",
    }
    return render_package_label_sheet(
        CONSIGNMENT, [], [{"line_id": "1", "products": [product]}],
        language, ["ADR"])


def lq_shapes(path):
    """The drawn paths on the page carrying the diamond of 3.4.7.1.

    Measured from the drawings rather than from pixels. The first version of
    this test thresholded the page and took the extent of everything dark,
    which swept the caption in with the figure and reported the mark as 176 mm
    across — a failure of the ruler, not of the mark.
    """
    with pymupdf.open(str(path)) as document:
        for page in document:
            if "3.4.7.1" in page.get_text():
                return [item["rect"] for item in page.get_drawings()]
    return []


def test_the_limited_quantities_mark_is_a_hundred_millimetres_a_side():
    """3.4.7.1: minimum 100 mm x 100 mm, for a square set at 45 degrees.

    Which puts it at 141.4 mm point to point, the same reading as the class
    labels — measured off the page rather than trusted, because the other
    reading of "100 mm x 100 mm" gives a 71 mm side and looks entirely right.
    """
    shapes = lq_shapes(limited_quantities_sheet())
    assert shapes, "the mark page carries no drawing"
    diamond = max(shapes, key=lambda r: r.width * r.height)
    width_mm = diamond.width / 72 * 25.4
    height_mm = diamond.height / 72 * 25.4
    assert round(width_mm, 1) == round(FULL_SIZE_MM, 1), width_mm
    assert round(height_mm, 1) == round(FULL_SIZE_MM, 1), height_mm
    assert round(width_mm / 2 ** 0.5) == 100


def test_the_black_portions_are_the_proportion_that_was_measured():
    """The one feature 3.4.7.1 leaves to "approximate proportion to those
    shown", measured off the edition's figure at 81 and 82 pixels of 353.

    Both portions are checked, because the figure is symmetric and an
    asymmetric drawing would mean the proportion was applied to one end only.
    """
    from app.services.documents.package_label_sheet import LQ_BLACK_PORTION

    shapes = sorted(lq_shapes(limited_quantities_sheet()),
                    key=lambda r: r.width * r.height, reverse=True)
    diamond, portions = shapes[0], shapes[1:3]
    assert len(portions) == 2, shapes
    for portion in portions:
        assert abs(portion.height / diamond.height - LQ_BLACK_PORTION) < 0.005, (
            portion.height / diamond.height)


def test_the_mark_appears_once_however_many_lines_carry_it():
    """It says nothing about the substance — no number, no name, no class —
    so one page serves every line that needs it."""
    product = {
        "un_number": "1263", "proper_shipping_name": "VERF", "class": "3",
        "labels": "3", "packing_group": "II", "limited_quantity": "5 L",
        "net_per_inner_packaging": "1 L", "gross_mass_per_package": "10 kg",
    }
    path = render_package_label_sheet(
        CONSIGNMENT, [], [{"line_id": "1", "products": [product, dict(product)]}],
        "nl", ["ADR"])
    assert sum(1 for text in pages(path) if "3.4.7.1" in text) == 1


def test_the_mark_page_names_the_unit_marking_without_deciding_it():
    """3.4.13 and 3.4.14 turn on the mass of the whole load. This check sees
    one consignment, so both are named and neither is applied."""
    text = next(t for t in pages(limited_quantities_sheet()) if "3.4.7.1" in t)
    flat = text.replace("\n", " ")
    for provision in ("3.4.15", "3.4.13", "3.4.14", "3.4.8"):
        assert provision in flat, provision


def test_the_mark_page_renders_in_every_language():
    for language in ("nl", "en", "de", "fr"):
        assert any("3.4.7.1" in t
                   for t in pages(limited_quantities_sheet(language))), language


# These fixtures exercise document/retention behaviour with optional review off.
pytestmark = pytest.mark.usefixtures("dg_review_disabled")
