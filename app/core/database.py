# app/models/database.py
from sqlalchemy import create_engine, Column, Integer, String, JSON, ForeignKey, Table
from sqlalchemy.orm import relationship, declarative_base, sessionmaker

# Create database engine
SQLALCHEMY_DATABASE_URL = "sqlite:///./forms.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

# Create declarative base
Base = declarative_base()

# Many-to-many association table
form_user = Table(
    'form_user',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('form_id', Integer, ForeignKey('forms.id'), primary_key=True),
    Column('state', String, default='initial'),  # initial, in_progress, finished, analyzed
    Column('json_begin', JSON),
    Column('json_response', JSON)
)


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String)

    # Relationship
    forms = relationship("Form", secondary=form_user, back_populates="users")


class Form(Base):
    __tablename__ = 'forms'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    json_structure = Column(JSON)
    category = Column(String)
    state = Column(String, default='draft')  # draft, started, finished

    # Relationship
    users = relationship("User", secondary=form_user, back_populates="forms")


# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Function to recreate the database
def create_database():
    # Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    create_database()
    print("Database recreated successfully!")
