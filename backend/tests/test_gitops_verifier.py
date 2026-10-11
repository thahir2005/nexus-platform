from unittest.mock import Mock, patch

from app.services.gitops_verifier import GitOpsVerifier


PUBLISHED_REVISION = "a" * 40
APPLIED_REVISION = "b" * 40


def manifest(build_id=66):
    return f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nexus-nexus-safe-demo
  namespace: nexus
  annotations:
    nexus.io/build-id: "{build_id}"
spec:
  template:
    metadata:
      annotations:
        nexus.io/build-id: "{build_id}"
"""


def response(text=None, json_data=None):
    result = Mock()
    result.text = text
    result.json.return_value = json_data
    result.raise_for_status.return_value = None
    return result


def configure_settings(mock_settings):
    mock_settings.gitops_repo_url = (
        "https://github.com/thahir2005/nexus-platform.git"
    )
    mock_settings.gitops_root_path = "infrastructure/gitops/apps"


def verify():
    return GitOpsVerifier().verify_deployment(
        revision=APPLIED_REVISION,
        published_revision=PUBLISHED_REVISION,
        project_name="NEXUS",
        environment_name="development",
        application_name="nexus-nexus-safe-demo",
        namespace="nexus",
        build_id=66,
    )


@patch("app.services.gitops_verifier.settings")
@patch("app.services.gitops_verifier.httpx.get")
def test_verifies_ancestor_and_matching_build(mock_get, mock_settings):
    configure_settings(mock_settings)
    mock_get.side_effect = [
        response(json_data={"status": "ahead"}),
        response(text=manifest(66)),
    ]

    result = verify()

    assert result["verified"] is True
    assert mock_get.call_count == 2
    assert "/compare/" in mock_get.call_args_list[0].args[0]
    assert "/nexus/development/application.yaml" in (
        mock_get.call_args_list[1].args[0]
    )


@patch("app.services.gitops_verifier.settings")
@patch("app.services.gitops_verifier.httpx.get")
def test_accepts_identical_revision_and_matching_build(
    mock_get, mock_settings
):
    configure_settings(mock_settings)
    mock_get.side_effect = [
        response(json_data={"status": "identical"}),
        response(text=manifest(66)),
    ]

    assert verify()["verified"] is True


@patch("app.services.gitops_verifier.settings")
@patch("app.services.gitops_verifier.httpx.get")
def test_rejects_unrelated_revision(mock_get, mock_settings):
    configure_settings(mock_settings)
    mock_get.return_value = response(json_data={"status": "diverged"})

    result = verify()

    assert result["verified"] is False
    assert "does not descend" in result["message"]
    assert mock_get.call_count == 1


@patch("app.services.gitops_verifier.settings")
@patch("app.services.gitops_verifier.httpx.get")
def test_rejects_mismatched_build(mock_get, mock_settings):
    configure_settings(mock_settings)
    mock_get.side_effect = [
        response(json_data={"status": "ahead"}),
        response(text=manifest(65)),
    ]

    result = verify()

    assert result["verified"] is False
    assert "build ID" in result["message"]


def test_rejects_missing_applied_revision():
    result = GitOpsVerifier().verify_deployment(
        revision=None,
        published_revision=PUBLISHED_REVISION,
        project_name="NEXUS",
        environment_name="development",
        application_name="nexus-nexus-safe-demo",
        namespace="nexus",
        build_id=66,
    )

    assert result["verified"] is False


def test_rejects_missing_published_revision():
    result = GitOpsVerifier().verify_deployment(
        revision=APPLIED_REVISION,
        published_revision=None,
        project_name="NEXUS",
        environment_name="development",
        application_name="nexus-nexus-safe-demo",
        namespace="nexus",
        build_id=66,
    )

    assert result["verified"] is False


@patch("app.services.gitops_verifier.settings")
@patch("app.services.gitops_verifier.httpx.get")
def test_rejects_missing_deployment(mock_get, mock_settings):
    configure_settings(mock_settings)
    mock_get.side_effect = [
        response(json_data={"status": "ahead"}),
        response(
            text=(
                "apiVersion: v1\n"
                "kind: Service\n"
                "metadata:\n"
                "  name: other\n"
            )
        ),
    ]

    result = verify()

    assert result["verified"] is False
    assert "Deployment" in result["message"]


@patch("app.services.gitops_verifier.settings")
@patch("app.services.gitops_verifier.httpx.get")
def test_rejects_unavailable_comparison(mock_get, mock_settings):
    import httpx

    configure_settings(mock_settings)
    mock_get.side_effect = httpx.TimeoutException("request timed out")

    result = verify()

    assert result["verified"] is False
    assert "Unable to verify" in result["message"]
