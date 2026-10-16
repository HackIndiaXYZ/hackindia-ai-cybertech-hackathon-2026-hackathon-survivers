from sqlalchemy import inspect, text

from backend.app.database import Base, engine
from backend.app.models import Complaint, TicketHistory

Base.metadata.create_all(bind=engine)

inspector = inspect(engine)
columns = {column["name"] for column in inspector.get_columns("complaints")}

if "department" not in columns:
    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE complaints ADD COLUMN department VARCHAR(100)")
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_complaints_department "
                "ON complaints (department)"
            )
        )

print("Database schema updated successfully.")
