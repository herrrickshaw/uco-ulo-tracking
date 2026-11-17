"""Characterisation test: API outputs on the deterministic seed (random.Random(42)) must not drift.

The golden file was captured from the pre-refactor code (commit dfebcb0).
"""
import json
from pathlib import Path

import pytest

GOLDEN = json.loads((Path(__file__).parent / "golden_seed_outputs.json").read_text())


@pytest.mark.parametrize("path", sorted(GOLDEN))
def test_seed_output_unchanged(client, path):
    resp = client.get(path)
    assert resp.status_code == 200
    assert json.loads(json.dumps(resp.json(), sort_keys=True, default=str)) == GOLDEN[path]
