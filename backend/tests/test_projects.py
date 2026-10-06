from app.db.session import SessionLocal
from app.models.project import Project
from app.models.user import User


def test_project_creation():
    db = SessionLocal()

    try:
        user = User(
            username="test-user",
            email="test@nexus.local",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        project = Project(
            name="test-project",
            description="Test NEXUS project",
            repository_url="https://github.com/test/project",
            owner_id=user.id,
        )

        db.add(project)
        db.commit()
        db.refresh(project)

        assert project.id is not None
        assert project.name == "test-project"
        assert project.owner_id == user.id

    finally:
        db.query(Project).filter(
            Project.name == "test-project"
        ).delete()

        db.query(User).filter(
            User.username == "test-user"
        ).delete()

        db.commit()
        db.close()