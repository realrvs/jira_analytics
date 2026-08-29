from app.core.database import engine, Base
from app.models.sqlalchemy import user, project, jira, analytics
Base.metadata.create_all(bind=engine)
print("Tables created successfully")