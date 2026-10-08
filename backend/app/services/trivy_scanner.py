import json
import subprocess
from dataclasses import dataclass


@dataclass
class TrivyScanResult:
    status: str
    unknown_count: int
    low_count: int
    medium_count: int
    high_count: int
    critical_count: int
    message: str
    findings: list[dict]


def scan_image(image_name: str) -> TrivyScanResult:
    command = [
        "trivy",
        "image",
        "--format",
        "json",
        "--scanners",
        "vuln",
        image_name,
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError("Trivy scan timed out") from exc

    if result.returncode != 0:
        raise ValueError(
            f"Trivy scan failed: {result.stderr.strip()}"
        )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("Unable to parse Trivy JSON output") from exc

    counts = {
        "UNKNOWN": 0,
        "LOW": 0,
        "MEDIUM": 0,
        "HIGH": 0,
        "CRITICAL": 0,
    }

    findings = []

    for target in data.get("Results", []):
        for vulnerability in target.get("Vulnerabilities") or []:
            severity = vulnerability.get("Severity", "UNKNOWN")
            counts[severity] = counts.get(severity, 0) + 1

            findings.append(
                {
                    "vulnerability_id": vulnerability.get("VulnerabilityID"),
                    "package": vulnerability.get("PkgName"),
                    "installed_version": vulnerability.get("InstalledVersion"),
                    "fixed_version": vulnerability.get("FixedVersion"),
                    "severity": severity,
                    "title": vulnerability.get("Title"),
                    "target": target.get("Target"),
                }
            )

    if counts["CRITICAL"] > 0 or counts["HIGH"] > 0:
        status = "blocked"
        message = (
            "Security gate blocked: HIGH or CRITICAL "
            "vulnerabilities detected"
        )
    else:
        status = "passed"
        message = (
            "Security gate passed: no HIGH or CRITICAL "
            "vulnerabilities detected"
        )

    return TrivyScanResult(
        status=status,
        unknown_count=counts["UNKNOWN"],
        low_count=counts["LOW"],
        medium_count=counts["MEDIUM"],
        high_count=counts["HIGH"],
        critical_count=counts["CRITICAL"],
        message=message,
        findings=findings,
    )
