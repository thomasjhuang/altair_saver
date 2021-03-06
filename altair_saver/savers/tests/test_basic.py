import json
import os
from typing import Any, Dict, Iterator, Tuple

import pytest

from altair_saver.savers import BasicSaver


def get_testcases() -> Iterator[Tuple[str, Dict[str, Any]]]:
    directory = os.path.join(os.path.dirname(__file__), "testcases")
    cases = set(f.split(".")[0] for f in os.listdir(directory))
    for case in sorted(cases):
        with open(os.path.join(directory, f"{case}.vl.json")) as f:
            spec = json.load(f)
        yield case, spec


@pytest.mark.parametrize("case, spec", get_testcases())
def test_basic_saver(case: str, spec: Dict[str, Any]) -> None:
    saver = BasicSaver(spec)
    bundle = saver.mimebundle("vega-lite")
    assert bundle.popitem()[1] == spec


def test_bad_format() -> None:
    saver = BasicSaver({})
    with pytest.raises(ValueError):
        saver.mimebundle("vega")
