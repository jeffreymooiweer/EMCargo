"""The register of source documents, and what it promises.

``backend/seed/dg/sources.json`` is the durable half of the regulatory
database: the documents live in a store outside the repository, and this file
is what proves which exact files the facts were read from. A register nobody
checks decays into a wish list, so these tests pin the properties the
architecture depends on.

What is deliberately *not* tested here is the store itself — CI runners have no
``/data`` and an empty store is a legitimate state. The one bridge test runs
only where documents are actually present.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "backend" / "seed" / "dg" / "sources.json"


def register():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_de_ids_zijn_uniek_en_de_velden_compleet():
    docs = register()["documents"]
    ids = [doc["id"] for doc in docs]
    assert len(ids) == len(set(ids))
    for doc in docs:
        for field in ("id", "title", "publisher", "edition", "language",
                      "profiles", "role", "filename", "urls", "obtained",
                      "sha256", "note"):
            assert field in doc, f"{doc['id']} lacks {field}"
        assert doc["language"] in {"nl", "en", "fr", "de"}
        assert doc["profiles"], doc["id"]


def test_elke_bron_zonder_url_draagt_een_gepinde_hash():
    """A download can be repeated; an operator-supplied file cannot. For those
    the pinned hash is the only proof of which file the facts came from, so it
    may never be absent.

    The models of 5.4.3 are the exception, and a reasoned one: they are not
    sources at all but pages served back out of a source. A model that is cut
    from an edition inherits that edition's pinned hash — the range says which
    pages — and one that nobody has supplied yet has no file to hash. Both are
    held to their own rule below.
    """
    for doc in register()["documents"]:
        if doc.get("model_of"):
            continue
        if not doc["urls"]:
            assert re.fullmatch(r"[0-9a-f]{64}", doc["sha256"] or ""), doc["id"]


def test_een_model_van_5_4_3_wijst_naar_een_editie_of_zegt_dat_het_ontbreekt():
    documents = {doc["id"]: doc for doc in register()["documents"]}
    for doc in documents.values():
        if not doc.get("model_of"):
            continue
        cut = doc.get("cut_from")
        if cut is None:
            assert doc["sha256"] is None, doc["id"]
            continue
        source = documents[cut["document"]]
        assert re.fullmatch(r"[0-9a-f]{64}", source["sha256"] or ""), doc["id"]
        first, last = cut["pages"]
        assert 0 < first <= last, doc["id"]


def test_het_leesscript_en_het_register_kennen_dezelfde_documenten():
    """read_land_regulations.py keeps its own SOURCES for the download ladder.
    If a document exists there but not in the register, the store tool cannot
    manage it and the architecture has quietly forked."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import read_land_regulations as reader

    registered = {doc["id"] for doc in register()["documents"]}
    assert set(reader.SOURCES) <= registered


def test_de_werkstroom_haalt_op_wat_het_register_kent():
    workflow = (ROOT / ".github" / "workflows" / "fetch-regulations.yml").read_text(
        encoding="utf-8")
    assert "regulations_store.py fetch" in workflow
    assert "/tmp/emcargo-regulations" in workflow


def test_het_gereedschap_meldt_de_stand(tmp_path):
    """`status` must run and speak, whatever the store holds — it is the
    command a future session starts with."""
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(ROOT / "scripts" / "regulations_store.py"), "status"],
        capture_output=True, text=True,
        env={"PATH": "/usr/bin:/bin", "EMCARGO_REGULATIONS_DIR": str(tmp_path)},
    )
    assert "store:" in result.stdout
    for doc in register()["documents"]:
        assert doc["id"] in result.stdout


@pytest.mark.skipif(not Path("/data/regulations").is_dir(),
                    reason="no document store on this machine")
def test_aanwezige_documenten_kloppen_met_hun_hash():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "regulations_store.py"), "verify"],
        capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 0, result.stdout + result.stderr
