from app.services.gitops_publisher import GitOpsPublisher


def test_slugify_project_name():
    assert GitOpsPublisher._slug("Student API") == "student-api"
    assert GitOpsPublisher._slug("devops_production") == "devops-production"
    assert GitOpsPublisher._slug("!!!") == "app"
