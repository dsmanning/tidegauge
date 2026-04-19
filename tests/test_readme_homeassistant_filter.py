from pathlib import Path


def test_readme_documents_homeassistant_filter_pipeline() -> None:
    content = Path("README.md").read_text(encoding="utf-8")

    assert "## Home Assistant Filtering" in content
    assert "homeassistant/tide_gauge_filter.yaml" in content
    assert "last valid" in content
    assert "10-minute rolling median" in content
    assert "outlier" in content
    assert "low-pass" in content
