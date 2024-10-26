# testing.py
from app.core.database import SessionLocal, User, Form


def test_database():
    db = SessionLocal()
    try:
        # Create a user
        user = User(name="John Doe", category="student")
        db.add(user)

        # Create a form
        form = Form(
            title="Survey 2024",
            description="Annual survey",
            json_structure={"questions": ["q1", "q2"]},
            category="annual",
            state="draft"
        )
        db.add(form)

        # Associate user with form
        form.users.append(user)

        # Commit the changes
        db.commit()

        print("Test data inserted successfully!")

    except Exception as e:
        print(f"An error occurred: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    test_database()
