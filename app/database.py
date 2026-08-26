from datetime import date
from typing import Optional
from sqlmodel import Field, SQLModel, Session, create_engine, select

class Workout(SQLModel, table = True):
    id: Optional[int] = Field(default = None, primary_key = True)
    date: date
    sport: str
    duration: int
    rpe: int
    notes: Optional[str] = None
    source: str = "manual"

class EnduranceDetails(SQLModel, table = True):
    __tablename__ = "endurance_details"

    workout_id: Optional[int] = Field(
        default = None,
        primary_key = True,
        foreign_key = "workout.id",
    )
    distance: float
    elevation_gain: Optional[float] = None
    average_hr: Optional[int] = None
    max_hr: Optional[int] = None

DATABASE_URL = "sqlite:///iron.db"

engine = create_engine(DATABASE_URL)

def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)

def save_workout(
    workout: Workout,
    endurance_details: Optional[EnduranceDetails] = None,
) -> Workout:
    with Session(engine) as session:
        session.add(workout)
        session.flush()

        if endurance_details is not None:
            endurance_details.workout_id = workout.id
            session.add(endurance_details)

        session.commit()
        session.refresh(workout)
        return workout

def get_workouts() -> list[tuple[Workout, Optional[EnduranceDetails]]]:
    with Session(engine) as session:
        statement = (
            select(Workout, EnduranceDetails)
            .join(EnduranceDetails, isouter = True)
            .order_by(Workout.date.desc(), Workout.id.desc())
        )
        return list(session.exec(statement).all())
