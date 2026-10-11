from urllib.parse import urlparse

import httpx


def check_application_health(
    health_url: str | None,
    timeout_seconds: float = 3.0,
) -> dict[str, str | int | None]:
    """Check an explicitly configured application health endpoint."""

    if not health_url:
        return {
            "status": "unconfigured",
            "url": None,
            "http_status": None,
            "message": "No application health URL configured",
        }

    parsed_url = urlparse(health_url)

    if (
        parsed_url.scheme != "https"
        or not parsed_url.hostname
        or parsed_url.username
        or parsed_url.password
    ):
        return {
            "status": "unconfigured",
            "url": health_url,
            "http_status": None,
            "message": "A valid HTTPS health URL is required",
        }

    try:
        with httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=False,
        ) as http:
            response = http.get(health_url)

        if 200 <= response.status_code < 300:
            return {
                "status": "healthy",
                "url": health_url,
                "http_status": response.status_code,
                "message": "Application health check succeeded",
            }

        return {
            "status": "unhealthy",
            "url": health_url,
            "http_status": response.status_code,
            "message": "Application health endpoint returned a non-success status",
        }

    except httpx.TimeoutException:
        return {
            "status": "unavailable",
            "url": health_url,
            "http_status": None,
            "message": "Application health check timed out",
        }

    except httpx.RequestError:
        return {
            "status": "unavailable",
            "url": health_url,
            "http_status": None,
            "message": "Application health endpoint could not be reached",
        }
