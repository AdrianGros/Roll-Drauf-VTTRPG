from tools.robots.strict_journey import (
    Finding,
    Rect,
    check_document_geometry,
    check_critical_geometry,
    classify_response,
)


def test_document_geometry_catches_horizontal_overflow_but_allows_normal_vertical_scroll():
    findings = check_document_geometry(
        viewport=Rect(0, 0, 1440, 900),
        document=Rect(0, 0, 1512, 1160),
        scroll_container=Rect(0, 0, 1440, 900),
        checkpoint="dashboard-settled",
        role="dm",
        viewport_name="desktop",
    )

    assert [finding.category for finding in findings] == ["layout"]
    assert all(finding.severity == "high" for finding in findings)
    assert all(finding.checkpoint == "dashboard-settled" for finding in findings)


def test_critical_geometry_catches_overlap_and_offscreen_controls():
    findings = check_critical_geometry(
        elements={
            "primary-nav": Rect(100, 20, 500, 70),
            "dashboard-heading": Rect(120, 55, 420, 120),
            "primary-cta": Rect(1500, 200, 1660, 250),
        },
        viewport=Rect(0, 0, 1440, 900),
        checkpoint="dashboard-settled",
        role="dm",
        viewport_name="desktop",
        overlap_pairs=(("primary-nav", "dashboard-heading"),),
    )

    assert any("overlap" in finding.actual for finding in findings)
    assert any("exceeds viewport horizontally" in finding.actual for finding in findings)
    assert all(finding.category == "visual" for finding in findings)


def test_critical_geometry_allows_vertical_document_growth():
    findings = check_critical_geometry(
        elements={"dashboard-page": Rect(100, 80, 1340, 3060)},
        viewport=Rect(0, 0, 1440, 900),
        checkpoint="dashboard-settled",
        role="dm",
        viewport_name="desktop",
    )

    assert findings == []


def test_response_classification_requires_allowlisting_expected_negative_responses():
    assert classify_response(404, "https://vtt.test/api/expected", expected=True) is None

    finding = classify_response(404, "https://vtt.test/static/fonts/book.woff2", expected=False)

    assert isinstance(finding, Finding)
    assert finding.category == "network"
    assert finding.severity == "high"


def test_auth_recovery_status_can_be_allowlisted_without_masking_asset_failures():
    assert classify_response(401, "https://vtt.test/api/auth/login", expected=True) is None

    finding = classify_response(401, "https://vtt.test/static/app.js", expected=False)

    assert isinstance(finding, Finding)
    assert finding.category == "network"
