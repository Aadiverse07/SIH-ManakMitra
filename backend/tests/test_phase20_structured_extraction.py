from backend.app.services.documents.parser import ParsedPage
from backend.app.services.documents.structured_extraction import extract_structures, normalize_formula, classify_requirement

TECH = """1 Scope
This standard specifies requirements for concrete.
2 Terms and definitions
2.1 Concrete means a composite material of cement, aggregate and water.
3 Requirements
The concrete shall have a strength of not less than 20 MPa.
The laboratory shall test specimens in accordance with the specified test method.
The procedure should preferably use calibrated equipment.
4 Calculation
Formula: f_c = P/A
where f_c = compressive strength, P = applied load, A = loaded area.
Table 1 — Minimum strength
Grade  Value (MPa)  Age (days)
M20    20           28
M25    25           28
Note: Values are minimum requirements.
Annex A — Test method
Example: A representative specimen may be selected.
References
[1] Referenced document.
"""

def test_clause_and_definition_extraction():
    s = extract_structures([ParsedPage(3, TECH, "text", "Scope", "1")])
    assert any(x["clause_number"] == "2.1" for x in s["clauses"])
    assert any(x["term"] == "Concrete" for x in s["definitions"])


def test_formula_normalization_has_readable_and_latex_forms():
    f = normalize_formula(r"$ f_c = \\frac{P}{A} $")
    assert f["latex"] == r"f_c = \\frac{P}{A}"
    assert "f₍c₎" in f["plain_text"]
    assert "/" in f["plain_text"]


def test_table_preserves_rows_units_and_page():
    s = extract_structures([ParsedPage(7, TECH, "text", "Requirements", "3")])
    table = s["tables"][0]
    assert table["table_number"] == "1"
    assert table["headers"][:2] == ["Grade", "Value (MPa)"]
    assert table["rows"][0][0] == "M20"
    assert "MPa" in table["units"]
    assert table["page_number"] == 7


def test_requirement_classification_is_conservative_and_testing_specific():
    assert classify_requirement("The laboratory shall test specimens.")[0] == "TESTING"
    assert classify_requirement("The concrete shall have 20 MPa.")[0] == "MANDATORY"
    assert classify_requirement("The procedure should preferably use calibrated equipment.")[0] == "RECOMMENDED"
    assert classify_requirement("This shall not be used above the stated limit.")[0] == "LIMITATION"
    assert classify_requirement("A random sentence without a directive.")[0] is None


def test_notes_examples_annexures_references_are_identified():
    s = extract_structures([ParsedPage(8, TECH, "text", None, None)])
    kinds = {x["section_type"] for x in s["context_items"]}
    assert {"NOTE", "EXAMPLE", "ANNEXURE", "REFERENCE"}.issubset(kinds)
