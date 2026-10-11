from unittest.mock import Mock, patch

import httpx

from app.services.application_health import check_application_health


def test_health_check_succeeds_for_http_200():
    response = Mock(status_code=200)

    with patch("app.services.application_health.httpx.Client") as client_class:
        client_class.return_value.__enter__.return_value.get.return_value = (
            response
        )

        result = check_application_health(
            "https://app.example.com/health"
        )

    assert result["status"] == "healthy"
    assert result["http_status"] == 200


def test_health_check_fails_for_http_500():
    response = Mock(status_code=500)

    with patch("app.services.application_health.httpx.Client") as client_class:
        client_class.return_value.__enter__.return_value.get.return_value = (
            response
        )

        result = check_application_health(
            "https://app.example.com/health"
        )

    assert result["status"] == "unhealthy"
    assert result["http_status"] == 500


def test_health_check_is_unconfigured_without_url():
    result = check_application_health(None)

    assert result["status"] == "unconfigured"
    assert result["http_status"] is None


def test_health_check_rejects_non_https_url():
    result = check_application_health(
        "http://app.example.com/health"
    )

    assert result["status"] == "unconfigured"


def test_health_check_reports_timeout():
    with patch("app.services.application_health.httpx.Client") as client_class:
        client_class.return_value.__enter__.return_value.get.side_effect = (
            httpx.ReadTimeout("timed out")
        )

        result = check_application_health(
            "https://app.example.com/health"
        )

    assert result["status"] == "unavailable"
    assert result["http_status"] is None


def test_health_check_reports_connection_failure():
    with patch("app.services.application_health.httpx.Client") as client_class:
        client_class.return_value.__enter__.return_value.get.side_effect = (
            httpx.ConnectError("connection failed")
        )

        result = check_application_health(
            "https://app.example.com/health"
        )

    assert result["status"] == "unavailable"
