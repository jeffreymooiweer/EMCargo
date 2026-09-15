"""The parser for the Dangerous Goods List of IMDG 42-24.

The list is a grid of eighteen columns across 170 landscape pages. What goes
wrong is not that such a parser falls over, but that it shifts a column or reads
a continuation line as a new substance — and then there are 2,300 substances with
the wrong segregation code in the app without anybody noticing.

These tests run on rebuilt pages with invented substances at the real x
positions. They record the geometry and the row logic, not the content of the
Code; that does not belong in this repo.
"""

import importlib.util
import sys
from pathlib import Path

_PATH = Path(__file__).resolve().parents[2] / "scripts" / "extract_imdg_dgl.py"
_spec = importlib.util.spec_from_file_location("extract_imdg_dgl", _PATH)
dgl = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = dgl
_spec.loader.exec_module(dgl)

# The grid as p627 actually draws it: twenty-two rules, so twenty-one cells. The
# number band puts the column number from the Code above each cell, except above
# the gutter between the two halves of the spread.
RULES = [42.5, 65.2, 189.9, 218.3, 255.1, 289.1, 326.0, 362.8, 399.7, 439.4,
         476.2, 515.9, 552.8, 637.8, 654.8, 694.5, 731.3, 771.0, 827.7, 884.4,
         1125.3, 1148.0]
LABELS = ["1", "2", "3", "4", "5", "6", "7a", "7b", "8", "9", "10", "11",
          None, "12", "13", "14", "15", "16a", "16b", "17", "18"]
MARKERS = [((left + right) / 2, label)
           for (left, right), label in zip(zip(RULES, RULES[1:]), LABELS) if label]

BOUNDS = dgl.boundaries(RULES, MARKERS)


# --- De meetkunde -------------------------------------------------------------

def test_every_column_number_names_the_cell_it_stands_over():
    for x, label in MARKERS:
        assert dgl.column_of(x, BOUNDS) == dgl.COLUMN_NAMES[label], label


def test_the_columns_do_not_overlap_and_leave_no_gap():
    for (_, _, right), (_, left, _) in zip(BOUNDS, BOUNDS[1:]):
        assert right == left


def test_the_gutter_between_the_two_halves_stays_nameless():
    """The list appears as a spread on one landscape sheet. Between column (11)
    and column (12) sits eighty-five points of white with a rule on either side.
    That is a cell for the drawing and not a column for the Code; counting it
    shifted every column after it one place along."""
    assert dgl.column_of(595.0, BOUNDS).startswith("_unnamed")


def test_the_shipping_name_no_longer_bleeds_into_the_un_column():
    """Where it came apart. The shipping name starts at x 68; the estimate
    'halfway between two headings' put the boundary at 72, so the first word of
    every line of the name ended up in the UN column:
    "1354 TRINITROBENZENE, with by G". The drawn rule is at 65.2."""
    assert dgl.column_of(49.0, BOUNDS) == "un_number"
    assert dgl.column_of(68.0, BOUNDS) == "proper_shipping_name"


def test_the_right_hand_half_lands_where_it_belongs():
    """The second miss: stowage, segregation and properties ran into each other —
    'E SG7 Desensitized SG30 crystals. compartments air.'"""
    assert dgl.column_of(806.6, BOUNDS) == "stowage_and_handling"
    assert dgl.column_of(854.2, BOUNDS) == "segregation"
    assert dgl.column_of(886.4, BOUNDS) == "properties_and_observations"
    assert dgl.column_of(1128.0, BOUNDS) == "_un_number_repeat"
    assert dgl.column_of(644.4, BOUNDS) == "imo_tank_instructions"
    assert dgl.column_of(672.8, BOUNDS) == "tank_instructions"
    assert dgl.column_of(711.0, BOUNDS) == "tank_provisions"


def test_what_lies_outside_the_table_is_dropped_not_rounded_inwards():
    """The margin holds page numbers and the triangle marking an amended entry.
    Adding that to the nearest column would let it pass for data."""
    assert dgl.column_of(20.0, BOUNDS) == ""
    assert dgl.column_of(1160.0, BOUNDS) == ""


def test_without_rules_or_numbers_no_grid_is_invented():
    """Too few rules or no number band means a page laid out differently. That
    one is skipped and counted, not guessed at."""
    assert dgl.boundaries([100.0, 200.0], MARKERS) == []
    assert dgl.boundaries(RULES, []) == []


def test_a_grid_missing_a_column_we_depend_on_is_refused():
    without_segregation = [(x, label) for x, label in MARKERS if label != "16b"]
    assert dgl.boundaries(RULES, without_segregation) == []


def test_numbers_that_do_not_line_up_with_the_rules_are_refused():
    """Two numbers in one cell means rules and number band do not belong
    together. Then the whole layout is suspect."""
    crowded = [(100.0 + 3.0 * n, label) for n, (_x, label) in enumerate(MARKERS)]
    assert dgl.boundaries(RULES, crowded) == []


# --- De rijlogica -------------------------------------------------------------

def line(**cells) -> dict[str, str]:
    return cells


def test_a_continuation_line_joins_the_entry_above_it():
    """A long shipping name continues on the next text line while the column
    with the UN number stays empty. That is not a new substance."""
    entries = dgl.merge_rows([
        line(un_number="1203", proper_shipping_name="GASOLINE or PETROL or", **{"class": "3"}),
        line(proper_shipping_name="MOTOR SPIRIT"),
        line(un_number="1263", proper_shipping_name="PAINT", **{"class": "3"}),
    ])
    assert len(entries) == 2
    assert entries[0]["proper_shipping_name"] == "GASOLINE or PETROL or MOTOR SPIRIT"
    assert entries[1]["proper_shipping_name"] == "PAINT"


def test_a_continuation_line_can_extend_any_column():
    entries = dgl.merge_rows([
        line(un_number="2031", proper_shipping_name="NITRIC ACID", segregation="SG6 SG16"),
        line(segregation="SG17 SG36"),
    ])
    assert entries[0]["segregation"] == "SG6 SG16 SG17 SG36"


def test_the_change_marker_starts_a_new_entry_and_is_kept_as_a_fact():
    """42-24 puts a triangle before every amended UN number, and the PDF delivers
    that as one word: "△1361". As long as that did not count as a UN number, the
    row counted as a continuation line and was pulled into the substance above
    it: UN 1360 got "4.3 4.2 4.2 4.2" as its class and four EmS codes in a row."""
    entries = dgl.merge_rows([
        line(un_number="1360", proper_shipping_name="CALCIUM PHOSPHIDE",
             **{"class": "4.3"}, ems="F-G, S-N"),
        line(un_number="△1361", proper_shipping_name="CARBON",
             **{"class": "4.2"}, ems="F-A, S-J"),
    ])
    assert [e["un_number"] for e in entries] == ["1360", "1361"]
    assert entries[0]["class"] == "4.3"
    assert entries[1]["amended"] == "42-24"
    assert "amended" not in entries[0]


def test_two_packing_groups_stay_two_entries():
    """UN 1361 appears twice in the list, once per packing group. Those must not
    melt into a single line."""
    entries = dgl.merge_rows([
        line(un_number="1361", proper_shipping_name="CARBON", packing_group="II"),
        line(un_number="1361", proper_shipping_name="CARBON", packing_group="III"),
    ])
    assert [e["packing_group"] for e in entries] == ["II", "III"]


def test_a_continuation_before_any_entry_is_discarded():
    """At the top of a page there can be a remainder line from the previous page.
    Sticking that onto the first substance of this page would be wrong."""
    entries = dgl.merge_rows([
        line(proper_shipping_name="leftover from the previous page"),
        line(un_number="1203", proper_shipping_name="GASOLINE"),
    ])
    assert len(entries) == 1
    assert entries[0]["proper_shipping_name"] == "GASOLINE"


def test_the_repeated_un_column_is_dropped():
    """The list repeats the UN number on the right of the page. That is layout."""
    entries = dgl.merge_rows([
        line(un_number="1203", proper_shipping_name="GASOLINE", _un_number_repeat="1203"),
    ])
    assert "_un_number_repeat" not in entries[0]


def test_a_line_whose_first_cell_is_not_a_un_number_is_a_continuation():
    """A cell with '1,000 L' in the first column does not exist, but a number
    that happens to have four digits must not start a new substance when it sits
    somewhere else."""
    entries = dgl.merge_rows([
        line(un_number="1202", proper_shipping_name="DIESEL FUEL"),
        line(properties_and_observations="Flashpoint 3000 C"),
    ])
    assert len(entries) == 1
    assert "3000" in entries[0]["properties_and_observations"]


# --- De zelfcontrole ----------------------------------------------------------

def test_a_shifted_column_shows_up_as_disagreement():
    """The safety net: if the class column shifts, the comparison with the card
    data has to report it instead of letting it through."""
    good = [{"un_number": "1203", "class": "3", "ems": "F-E, S-E"}]
    shifted = [{"un_number": "1203", "class": "II", "ems": "F-E, S-E"}]
    assert dgl.cross_check(good)["class"]["differs"] == 0
    assert dgl.cross_check(shifted)["class"]["differs"] == 1


def test_the_cross_check_reports_an_agreement_ratio():
    result = dgl.cross_check([{"un_number": "1203", "class": "3"}])
    assert result["class"]["agreement"] == 1.0


def test_normalise_collapses_the_whitespace_a_pdf_leaves_behind():
    assert dgl.normalise({"a": "  two   words \n"}) == {"a": "two words"}
    assert dgl.normalise({"a": "   "}) == {}


# --- What the first trial run brought to light --------------------------------

class FakeRect:
    """A thin vertical rule around a given centre.

    find_rules looks at the centre of the rectangle, not at its left edge — a
    real rule has width and sits symmetrically about the boundary it marks.
    """

    def __init__(self, centre, height, width=0.7):
        self.x0, self.x1 = centre - width / 2, centre + width / 2
        self.width, self.height = width, height


class FakePage:
    def __init__(self, rects):
        self._rects = rects

    def get_drawings(self):
        return [{"rect": r} for r in self._rects]


def test_short_cell_borders_still_reveal_the_columns():
    """The list draws no column line across the page but frames each row block:
    the tallest vertical is some eighty points. Requiring a line to span half the
    page yielded zero of them — precisely the first failed trial run."""
    rects = []
    for x in (65.2, 189.9, 218.3, 255.1, 289.1):
        rects += [FakeRect(x, 78.1) for _ in range(20)]
    assert dgl.find_rules(FakePage(rects)) == [65.2, 189.9, 218.3, 255.1, 289.1]


def test_a_stray_line_is_not_mistaken_for_a_column_edge():
    """A real boundary recurs through the whole table; a stray rule does not."""
    rects = [FakeRect(65.2, 78.1) for _ in range(40)]
    rects += [FakeRect(190.0, 78.1) for _ in range(40)]
    rects.append(FakeRect(400.0, 20.0))
    assert 400.0 not in dgl.find_rules(FakePage(rects))


def test_borders_a_hair_apart_count_as_one_edge():
    rects = [FakeRect(189.9, 78.1) for _ in range(20)]
    rects += [FakeRect(190.6, 78.1) for _ in range(20)]
    assert dgl.find_rules(FakePage(rects)) == [189.9]  # the first centre counts


def test_a_page_without_drawings_yields_no_rules():
    assert dgl.find_rules(FakePage([])) == []


def test_the_body_window_clears_the_column_number_band():
    """At y 131.7 sit the column numbers '(1) (2) (3)' and at y 140.5 the
    references to the sections. Those came in as data."""
    assert dgl.BODY_TOP > 140.5


def test_a_cell_that_runs_past_its_column_is_flagged_not_swallowed():
    """'0289 CORD,' means the shipping name was read across the boundary.
    Skipping such a row would hide it; simply taking it along would produce a
    truncated name. It stays recognisable so the count reports it."""
    assert dgl.UN_OVERFLOW.match("0289 CORD,")
    assert not dgl.UN_OVERFLOW.match("0289")
    entries = dgl.merge_rows([line(un_number="0289 CORD,", proper_shipping_name="DETONATING,")])
    assert len(entries) == 1
    assert entries[0]["un_number"] == "0289 CORD,"


def test_the_alignment_no_longer_has_to_be_guessed():
    """Does the first rule found carry the outer edge of the table or already the
    first column separation? As long as the columns were counted in order, that
    made a difference of one place for every column and had to be guessed. With
    the number band there is nothing left to guess: every cell gets the name of
    the number above it, wherever the series begins."""
    extra_rule = sorted(RULES + [595.0])  # a stroke in the gutter
    shifted = dgl.boundaries(extra_rule, MARKERS)
    assert dgl.column_of(854.2, shifted) == "segregation"
    assert dgl.column_of(68.0, shifted) == "proper_shipping_name"


def test_rules_that_fit_no_numbers_yield_nothing():
    """Rules that connect to nothing on the number band are not a column layout.
    Then nothing is better than a grid that merely looks precise."""
    nonsense = [float(100 + 40 * n) for n in range(25)]
    assert dgl.boundaries(nonsense, MARKERS) == []


# --- Rijbanden ----------------------------------------------------------------

class FakeHRect:
    """A thin horizontal rule around a given centre."""

    def __init__(self, centre, width, height=0.7, x0=40.0):
        self.y0, self.y1 = centre - height / 2, centre + height / 2
        self.x0, self.x1 = x0, x0 + width
        self.width, self.height = width, height


class FakeWordPage:
    def __init__(self, words, rects=()):
        self._words, self._rects = words, list(rects)

    def get_text(self, kind):
        assert kind == "words"
        return self._words

    def get_drawings(self):
        return [{"rect": r} for r in self._rects]


def test_the_column_numbers_are_read_from_the_band_above_the_table():
    """At y 131.7 sits '(1) (2) (3) …', at y 140.5 the references to the sections
    governing each column. Only the first band carries names."""
    words = [
        (44.0, 131.7, 52.0, 140.0, "(1)", 0, 0, 0),
        (120.0, 131.7, 130.0, 140.0, "(2)", 0, 0, 1),
        (330.0, 131.7, 344.0, 140.0, "(7a)", 0, 0, 2),
        (840.0, 131.7, 858.0, 140.0, "(16b)", 0, 0, 3),
        (60.0, 140.5, 80.0, 148.0, "3.1.2", 0, 1, 0),
        (49.0, 205.0, 60.0, 215.0, "1203", 0, 2, 0),
    ]
    assert dgl.column_markers(FakeWordPage(words)) == [
        (48.0, "1"), (125.0, "2"), (337.0, "7a"), (849.0, "16b")]


def test_every_column_number_has_a_name():
    """A number the table does carry but this parser does not know would drop out
    as '_column_19' without anybody noticing."""
    for label in LABELS:
        if label is not None:
            assert label in dgl.COLUMN_NAMES


def test_row_rules_come_from_a_line_that_spans_the_table():
    page = FakeWordPage([], [FakeHRect(200.0, 1100.0), FakeHRect(260.0, 1100.0),
                             FakeHRect(230.0, 40.0)])  # sub-cell, not a row rule
    assert dgl.find_row_rules(page) == [200.0, 260.0]


def test_a_row_rule_drawn_in_pieces_counts_just_the_same():
    """This table puts its row rules down per cell, just like the column rules.
    Requiring one rectangle to span half the page found zero of them, and then
    the whole page became one band with twelve substances in it. What counts is
    how much width the fragments at the same height cover together."""
    pieces = []
    for y in (200.0, 260.0):
        pieces += [FakeHRect(y, 60.0, x0=40.0 + 60 * n) for n in range(18)]
    pieces.append(FakeHRect(230.0, 40.0, x0=300.0))  # a small rule inside a single cell
    assert dgl.find_row_rules(FakeWordPage([], pieces)) == [200.0, 260.0]


def test_a_word_lands_in_the_band_its_y_falls_in():
    assert dgl.band_of(180.0, [200.0, 260.0]) == 0
    assert dgl.band_of(210.0, [200.0, 260.0]) == 1
    assert dgl.band_of(300.0, [200.0, 260.0]) == 2


def test_two_entries_in_adjacent_bands_do_not_merge():
    """The y tolerance glued UN 0291 and UN 0292 into one entry with
    'ems': '- F-B, S-X - F-B, S-X'. With the row rules included it stays two."""
    words = [
        (49.0, 205.0, 60.0, 215.0, "0291", 0, 0, 0),
        (95.0, 205.0, 140.0, 215.0, "BOMBS", 0, 0, 1),
        (49.0, 265.0, 60.0, 275.0, "0292", 0, 1, 0),
        (95.0, 265.0, 150.0, 275.0, "GRENADES", 0, 1, 1),
    ]
    page = FakeWordPage(words)
    lines = dgl.page_lines(page, BOUNDS, row_rules=[200.0, 260.0, 320.0])
    entries = dgl.merge_rows(lines)
    assert [e["un_number"] for e in entries] == ["0291", "0292"]


def test_a_name_running_over_two_lines_stays_in_one_band():
    """Within one band the name may run over several text lines; the words then
    follow each other in reading order."""
    words = [
        (49.0, 205.0, 60.0, 215.0, "1203", 0, 0, 0),
        (95.0, 205.0, 140.0, 215.0, "GASOLINE", 0, 0, 1),
        (95.0, 218.0, 130.0, 228.0, "or", 0, 1, 0),
        (110.0, 218.0, 150.0, 228.0, "PETROL", 0, 1, 1),
    ]
    lines = dgl.page_lines(FakeWordPage(words), BOUNDS, row_rules=[200.0, 260.0])
    entries = dgl.merge_rows(lines)
    assert len(entries) == 1
    assert entries[0]["proper_shipping_name"] == "GASOLINE or PETROL"


def test_words_outside_the_body_window_are_ignored():
    words = [
        (49.0, 131.7, 60.0, 140.0, "(1)", 0, 0, 0),      # kolomnummerband
        (49.0, 205.0, 60.0, 215.0, "1203", 0, 1, 0),
        (49.0, 801.6, 60.0, 810.0, "579", 0, 2, 0),      # voettekst
    ]
    lines = dgl.page_lines(FakeWordPage(words), BOUNDS, row_rules=[200.0, 260.0])
    assert [c.get("un_number") for c in lines] == ["1203"]


class FakeVRect:
    """A vertical cell rule spanning exactly one row band."""

    def __init__(self, x, y0, y1, width=0.7):
        self.x0, self.x1 = x - width / 2, x + width / 2
        self.y0, self.y1 = y0, y1
        self.width, self.height = width, y1 - y0


def banded_page(bands, columns=18):
    rects = []
    for y0, y1 in bands:
        rects += [FakeVRect(65.0 + 60 * n, y0, y1) for n in range(columns)]
    return FakeWordPage([], rects)


def test_row_bands_come_from_the_vertical_segments_own_extents():
    """Every vertical cell rule runs across exactly one row, and there are
    eighteen of them side by side. Their tops and bottoms are therefore the row
    boundaries — information the first version threw away in order to look for
    horizontal lines that are barely there, after which the whole page became one
    band."""
    page = banded_page([(150.0, 228.0), (228.0, 306.0), (306.0, 384.0)])
    assert dgl.find_row_rules(page) == [150.0, 228.0, 306.0, 384.0]


def test_the_column_edges_still_come_out_of_the_same_rectangles():
    page = banded_page([(150.0, 228.0), (228.0, 306.0)])
    assert dgl.find_rules(page)[:3] == [65.0, 125.0, 185.0]


def test_the_change_marker_does_not_push_the_un_number_out_of_the_table():
    """The triangle sits before the number, so "△1361" starts to the left of the
    outer edge at x 42.5. Going by the left edge left those rows without a UN
    number and so pulled them into UN 1360 as continuation lines. The centre of
    the word does fall inside the column."""
    words = [
        (49.0, 205.0, 62.0, 215.0, "1360", 0, 0, 0),
        (36.0, 225.0, 62.0, 235.0, "△1361", 0, 1, 0),
    ]
    lines = dgl.page_lines(FakeWordPage(words), BOUNDS, row_rules=[200.0, 220.0, 260.0])
    assert [c.get("un_number") for c in lines] == ["1360", "△1361"]


def test_a_band_holding_several_short_entries_is_split_at_each_un_number():
    """The drawn rules frame a *block* of rows as soon as the entries are short.
    On p627 UN 1360, UN 1361 (two packing groups) and UN 1362 sat in one band
    like that, and came out as a single entry with class '4.3 4.2 4.2 4.2'. Every
    row begins with a UN number, so there should be a boundary above it — even
    where the table draws none."""
    words = [
        (49.0, 205.0, 62.0, 215.0, "1360", 0, 0, 0),
        (200.0, 205.0, 212.0, 215.0, "4.3", 0, 0, 1),
        (49.0, 225.0, 66.0, 235.0, "△1361", 0, 1, 0),
        (200.0, 225.0, 212.0, 235.0, "4.2", 0, 1, 1),
        (49.0, 245.0, 62.0, 255.0, "1362", 0, 2, 0),
        (200.0, 245.0, 212.0, 255.0, "4.2", 0, 2, 1),
    ]
    page = FakeWordPage(words, [FakeVRect(65.2, 200.0, 280.0) for _ in range(18)])
    entries = dgl.merge_rows(dgl.page_lines(page, BOUNDS,
                                            dgl.row_rules_for(page, BOUNDS)))
    assert [e["un_number"] for e in entries] == ["1360", "1361", "1362"]
    assert [e["class"] for e in entries] == ["4.3", "4.2", "4.2"]


def test_a_drawn_row_rule_and_a_un_number_do_not_make_two_boundaries():
    """The drawn rule coincides with the start of the row below it. Two
    boundaries in quick succession would put an empty band between every two
    rows."""
    words = [(49.0, 202.0, 62.0, 212.0, "1360", 0, 0, 0)]
    page = FakeWordPage(words, [FakeVRect(65.2, 200.0, 280.0) for _ in range(18)])
    assert dgl.row_rules_for(page, BOUNDS) == [199.0, 280.0]


def test_horizontal_rules_remain_the_fallback():
    """A page without vertical segments may still be divided on its horizontal
    rules."""
    page = FakeWordPage([], [FakeHRect(200.0, 1100.0), FakeHRect(260.0, 1100.0)])
    assert dgl.find_row_rules(page) == [200.0, 260.0]


# --- The self-check leans on an independent source ----------------------------
#
# The class first came from card_data.json, but those are the UN cards: an IMDG
# source too. That lays one IMDG reading next to another and measures nothing.
# Worse: for UN 2984 to 2992, 3548 and 3550 those cards carry sequence numbers in
# the class field, which produced eleven false deviations that were checked one
# by one. ADR Table A *is* independent of this PDF.

def test_the_class_check_reads_adr_and_not_the_un_cards():
    divisions = dgl.adr_divisions()
    assert len(divisions) > 2000
    # ADR gives only '1' for explosives and only '2' for gases; the list carries
    # the division in full, so those have to be brought into line.
    assert divisions["0004"] == {"1.1D"}
    assert divisions["1017"] == {"2.3"}
    assert divisions["1203"] == {"3"}


def test_the_substances_whose_cards_were_broken_now_read_correctly():
    """Exactly the numbers the old self-check raised a false alarm on."""
    divisions = dgl.adr_divisions()
    assert divisions["2984"] == {"5.1"}
    assert divisions["2988"] == {"4.3"}
    assert divisions["3548"] == {"9"}


def test_the_copied_division_rule_matches_the_one_in_the_application():
    """The extraction script runs in GitHub Actions with pymupdf only and cannot
    import the application, so this rule exists twice. This test is what keeps
    the copies from drifting apart.

    One difference is intended: where the application arrives at a bare "1" or
    "2", ADR has given no division, and then the script leaves the substance out
    altogether instead of comparing it. Everywhere the application *does* derive
    a division, they have to agree."""
    import json
    from pathlib import Path as _Path

    from app.services.dg.enrichment import parse_hazards

    seed = _Path(__file__).resolve().parents[1] / "seed" / "dg" / "un_numbers.json"
    entries = json.loads(seed.read_text(encoding="utf-8"))
    divisions = dgl.adr_divisions()

    for entry in entries:
        un = str(entry.get("un", "")).strip()
        expected = parse_hazards(entry)["division"]
        if expected and expected not in {"1", "2"}:
            assert expected in divisions.get(un, set()), un


def test_a_un_number_with_several_adr_entries_keeps_all_its_divisions():
    """UN 1950 (aerosols) appears in Table A as 2.1 *and* as 2.2. Remembering one
    of them would let the other half count as a deviation."""
    assert dgl.adr_divisions()["1950"] == {"2.1", "2.2"}


def test_a_class_that_heads_an_adr_division_counts_as_agreement():
    """The IMDG Code calls aerosols class 2 where ADR gives the division. That is
    not a contradiction but a difference in how finely the two classify."""
    assert dgl.division_matches("2", {"2.1", "2.2"})
    assert dgl.division_matches("2.1", {"2.1", "2.2"})
    assert not dgl.division_matches("3", {"2.1", "2.2"})
    assert not dgl.division_matches("", {"2.1"})


def test_a_substance_adr_forbids_on_the_road_is_left_out_of_the_comparison():
    """UN 2186 is not permitted by road and therefore has no label in Table A; by
    sea it is permitted and the IMDG Code names division 2.3. Laying those two
    against each other measures nothing — one source has no answer to it."""
    divisions = dgl.adr_divisions()
    assert "2186" not in divisions
    assert "2421" not in divisions


def test_an_article_referring_to_5_2_2_1_12_is_left_out_too():
    """'siehe 5.2.2.1.12': articles carry the labels of every hazard present, so
    ADR names no division here."""
    assert "3537" not in dgl.adr_divisions()


def test_a_class_that_is_never_divided_is_still_compared():
    """Classes 1 and 2 are always divided; 3, 8 and 9 are not. Leaving the latter
    out would shrink the safety net for no reason."""
    divisions = dgl.adr_divisions()
    assert divisions["1203"] == {"3"}
    assert divisions["3423"] == {"8"}


def test_the_un_cards_no_longer_carry_a_class():
    """The field was read by nothing in the application and was demonstrably
    wrong. Repairing what nobody reads is wasted effort; gone is better."""
    import json
    from pathlib import Path as _Path

    seed = _Path(__file__).resolve().parents[1] / "seed" / "dg" / "card_data.json"
    assert not seed.exists()
