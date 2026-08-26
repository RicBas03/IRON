"""SQLModel entities and persistence operations for IRON."""

from datetime import date
from typing import Optional
from sqlmodel import Field, SQLModel, Session, create_engine, select

# define the database models for workouts, endurance details, and goals
class Workout(SQLModel, table = True):
    id: Optional[int] = Field(default = None, primary_key = True)
    date: date
    sport: str
    duration: int
    rpe: int
    notes: Optional[str] = None
    source: str = "manual"

# define the database model for endurance details, which are specific to Run, Bike, and Swim workouts
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

# define the database model for athlete goals, which can be active or inactive and have a priority
class Goal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    goal_type: str
    category: str
    priority: int
    target_date: Optional[date] = None
    active: bool = True

# define the database connection and engine for SQLite
DATABASE_URL = "sqlite:///iron.db"

# create the database engine using the specified URL
engine = create_engine(DATABASE_URL)

# create the database and tables if they do not exist
def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)

# persist a workout and optional endurance details atomically
def save_workout(
    workout: Workout,
    endurance_details: Optional[EnduranceDetails] = None,
) -> Workout:
    with Session(engine) as session:
        session.add(workout)
        # flush assigns the workout id needed by the endurance foreign key
        session.flush()

        if endurance_details is not None:
            endurance_details.workout_id = workout.id
            session.add(endurance_details)

        session.commit()
        session.refresh(workout)
        return workout

# retrieve workouts with optional endurance details, ordered by date and id descending
def get_workouts() -> list[tuple[Workout, Optional[EnduranceDetails]]]:
    with Session(engine) as session:
        # The outer join keeps Gym workouts, which have no endurance row.
        statement = (
            select(Workout, EnduranceDetails)
            .join(EnduranceDetails, isouter = True)
            .order_by(Workout.date.desc(), Workout.id.desc())
        )
        return list(session.exec(statement).all())

# retrieve active goals ordered by priority and id descending
def get_active_goals() -> list[Goal]:
    with Session(engine) as session:
        statement = (
            select(Goal)
            .where(Goal.active)
            .order_by(Goal.priority.desc(), Goal.id)
        )
        return list(session.exec(statement).all())

# replace the active goal set while retaining inactive goal history
def replace_active_goals(goals: list[Goal]) -> list[Goal]:
    with Session(engine) as session:
        active_goals = session.exec(select(Goal).where(Goal.active)).all()

        for active_goal in active_goals:
            active_goal.active = False
            session.add(active_goal)

        session.add_all(goals)
        session.commit()

        for goal in goals:
            session.refresh(goal)

        return goals
