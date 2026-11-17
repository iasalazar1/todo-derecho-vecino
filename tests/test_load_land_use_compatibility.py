import argparse
import csv
import json
import subprocess
from collections import Counter

import pytest

from scripts import load_land_use_compatibility as loader


EXPECTED_STATES = {
    "permitido",
    "permitido (*)",
    "permitido (**)",
    "prohibido",
    "por validar",
}


def test_validate_preserves_all_table_22_states_and_cells():
    activities, rows = loader.validate(loader.DEFAULT_JSON)

    assert loader.STATES == EXPECTED_STATES
    assert len(activities) == 78
    assert len({activity["actividad_id"] for activity in activities}) == 78
    assert len(rows) == 546
    assert Counter(row["estado_original"] for row in rows) == {
        "permitido": 136,
        "permitido (*)": 13,
        "permitido (**)": 2,
        "por validar": 1,
        "prohibido": 394,
    }

    assert {
        (row["actividad_id"], row["zonificacion"], row["estado_original"])
        for row in rows
        if row["estado_original"] in {"permitido (*)", "permitido (**)"}
    } == {
        ("actividad_029", "H", "permitido (*)"),
        ("actividad_029", "HC", "permitido (*)"),
        ("actividad_032", "H", "permitido (*)"),
        ("actividad_032", "HC", "permitido (*)"),
        ("actividad_033", "H", "permitido (*)"),
        ("actividad_033", "HC", "permitido (*)"),
        ("actividad_037", "H", "permitido (*)"),
        ("actividad_038", "H", "permitido (*)"),
        ("actividad_054", "H", "permitido (*)"),
        ("actividad_054", "HC", "permitido (*)"),
        ("actividad_054", "HO", "permitido (*)"),
        ("actividad_054", "HM", "permitido (*)"),
        ("actividad_054", "HCS", "permitido (*)"),
        ("actividad_064", "H", "permitido (**)"),
        ("actividad_064", "HC", "permitido (**)"),
    }


def test_validate_rejects_states_outside_the_five_literals(tmp_path):
    source = json.loads(loader.DEFAULT_JSON.read_text(encoding="utf-8"))
    source[0]["zonificaciones"]["H"] = "Permitido"
    invalid_json = tmp_path / "tabla_22_invalid.json"
    invalid_json.write_text(json.dumps(source), encoding="utf-8")

    with pytest.raises(ValueError, match="estado no admitido"):
        loader.validate(invalid_json)


def test_apply_serialization_preserves_starred_states_without_dropping_rows(
    monkeypatch, tmp_path
):
    _, rows = loader.validate(loader.DEFAULT_JSON)
    passfile = tmp_path / "pgpass"
    passfile.write_text("test-only\n", encoding="utf-8")
    monkeypatch.setenv("PGPASSFILE", str(passfile))
    captured = {}

    def fake_run(command, input, capture_output, text):
        captured["sql"] = input
        copy_path = input.split("FROM '", 1)[1].split("'", 1)[0]
        with open(copy_path, encoding="utf-8", newline="") as source:
            captured["csv_rows"] = list(csv.DictReader(source))
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(loader.subprocess, "run", fake_run)
    loader.apply_rows(
        rows,
        argparse.Namespace(
            host="127.0.0.1",
            port=15432,
            username="tdv_admin",
            database="tododerechovecino",
        ),
    )

    serialized = captured["csv_rows"]
    assert len(serialized) == 546
    assert Counter(row["estado_original"] for row in serialized) == Counter(
        row["estado_original"] for row in rows
    )
    assert {row["estado_original"] for row in serialized} >= {
        "permitido (*)",
        "permitido (**)",
    }
    assert all(row["needs_review"] == "true" for row in serialized)
    assert "DROP CONSTRAINT IF EXISTS land_use_compatibility_estado_original_check" in captured["sql"]
    assert all(f"'{state}'" in captured["sql"] for state in EXPECTED_STATES)

    source_activity = next(
        activity
        for activity in json.loads(
            loader.DEFAULT_JSON.read_text(encoding="utf-8")
        )
        if activity["actividad_id"] == "actividad_029"
    )
    serialized_activity = next(
        row
        for row in serialized
        if row["actividad_id"] == "actividad_029"
        and row["zonificacion"] == "H"
    )
    assert serialized_activity["categoria"] == source_activity["categoria"]
    assert serialized_activity["subcategoria"] == source_activity["subcategoria"]
    assert serialized_activity["actividad_original"] == source_activity["actividad_original"]
    assert json.loads(serialized_activity["alias_busqueda"]) == source_activity["alias_busqueda"]
    assert serialized_activity["fuente_archivo"] == source_activity["fuente"]["archivo"]
    assert json.loads(serialized_activity["fuente_paginas"]) == source_activity["fuente"]["paginas"]
