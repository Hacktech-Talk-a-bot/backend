# example_crud_usage.py
from app.core.database import SessionLocal, create_database
from app.crud.operations import (
    create_user, create_form, assign_form_to_user,
    update_user_form_state, get_user_forms, get_users,
    update_form
)


def test_crud_operations():
    # Create a database session
    db = SessionLocal()
    try:
        # Create users
        user1 = create_user(db, name="John Doe", category="student")
        user2 = create_user(db, name="Jane Smith", category="teacher")
        print(f"Created users: {user1.name}, {user2.name}")

        # Create a form
        form1 = create_form(
            db,
            title="Annual Survey 2024",
            description="Feedback for the year 2024",
            json_structure={
                "questions": [
                    {"id": 1, "text": "How satisfied are you?"},
                    {"id": 2, "text": "Would you recommend us?"}
                ]
            },
            category="feedback"
        )
        print(f"Created form: {form1.title}")

        # Assign form to users
        assign_form_to_user(
            db,
            user1.id,
            form1.id,
            json_begin={"started_at": "2024-01-01"}
        )
        print(f"Assigned form to {user1.name}")

        # Update form state for user1
        update_user_form_state(
            db,
            user1.id,
            form1.id,
            state="in_progress",
            json_response={"question_1": "Very satisfied"}
        )
        print(f"Updated form state for {user1.name}")

        # Get all forms for user1
        user1_forms = get_user_forms(db, user1.id)
        print(f"\nForms for {user1.name}:")
        for form_data in user1_forms:
            print(f"- {form_data['title']}: {form_data['user_form_state']}")

        # Update form
        updated_form = update_form(
            db,
            form1.id,
            state="started",
            description="Updated description"
        )
        print(f"\nUpdated form state: {updated_form.state}")

        # List all users
        all_users = get_users(db)
        print("\nAll users:")
        for user in all_users:
            print(f"- {user.name} ({user.category})")

    finally:
        db.close()


if __name__ == "__main__":
    # Recreate the database
    create_database()

    # Run the test
    test_crud_operations()
