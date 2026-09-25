"""BIS source adapters.

This module deliberately does not call a public BIS API or scrape BIS.
The mock connector is the only included collector and is used for tests/local
development. A future authorized BIS API/API Setu or permitted data connector
can implement the same BISSource interface.
"""
from copy import deepcopy
from typing import Any


class MockBISSource:
    name = "mock_bis"

    def __init__(self, records: list[dict[str, Any]] | None = None, fail: bool = False):
        self.records = records or []
        self.fail = fail

    def collect(self) -> list[dict[str, Any]]:
        if self.fail:
            raise RuntimeError("Mock BIS source collection failed")
        return deepcopy(self.records)
