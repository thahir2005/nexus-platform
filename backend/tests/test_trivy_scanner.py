from unittest.mock import patch

from app.services.trivy_scanner import scan_image


def test_trivy_blocks_high_vulnerabilities():
    trivy_output = {
        "Results": [
            {
                "Vulnerabilities": [
                    {"Severity": "HIGH"},
                    {"Severity": "HIGH"},
                    {"Severity": "CRITICAL"},
                    {"Severity": "MEDIUM"},
                    {"Severity": "LOW"},
                ]
            }
        ]
    }

    with patch("app.services.trivy_scanner.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = __import__("json").dumps(trivy_output)
        mock_run.return_value.stderr = ""

        result = scan_image("test/image")

    assert result.status == "blocked"
    assert result.high_count == 2
    assert result.critical_count == 1
    assert result.medium_count == 1
    assert result.low_count == 1


def test_trivy_passes_without_high_or_critical():
    trivy_output = {
        "Results": [
            {
                "Vulnerabilities": [
                    {"Severity": "MEDIUM"},
                    {"Severity": "LOW"},
                    {"Severity": "UNKNOWN"},
                ]
            }
        ]
    }

    with patch("app.services.trivy_scanner.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = __import__("json").dumps(trivy_output)
        mock_run.return_value.stderr = ""

        result = scan_image("test/image")

    assert result.status == "passed"
    assert result.high_count == 0
    assert result.critical_count == 0
    assert result.medium_count == 1
    assert result.low_count == 1
    assert result.unknown_count == 1