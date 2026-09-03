"""SQLModel entities and persistence operations for IRON."""

from datetime import date, datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Session, create_engine, select

# define the database models for workouts, endurance details, and goals
class Workout(SQLModel, table = True):
    id: Optional[int] = Field(default = None, primary_key = True)
    performed_at: datetime
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

# define planned sessions separately from completed workout history
class PlannedWorkout(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    scheduled_at: datetime
    sport: str
    workout_type: str
    target_duration: Optional[int] = None
    target_distance: Optional[float] = None
    notes: Optional[str] = None
    status: str = "planned"

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
def get_workouts(
    start_at: Optional[datetime] = None,
    end_at: Optional[datetime] = None,
) -> list[tuple[Workout, Optional[EnduranceDetails]]]:
    with Session(engine) as session:
        # the outer join keeps Gym workouts, which have no endurance row
        statement = select(Workout, EnduranceDetails).join(
            EnduranceDetails,
            isouter=True,
        )
        if start_at is not None:
            statement = statement.where(Workout.performed_at >= start_at)
        if end_at is not None:
            statement = statement.where(Workout.performed_at < end_at)
        statement = statement.order_by(
            Workout.performed_at.desc(),
            Workout.id.desc(),
        )
        return list(session.exec(statement).all())

# retrieve a single workout with optional endurance details by primary key
def get_workout_by_id(
    workout_id: int,
) -> Optional[tuple[Workout, Optional[EnduranceDetails]]]:
    with Session(engine) as session:
        statement = (
            select(Workout, EnduranceDetails)
            .join(EnduranceDetails, isouter=True)
            .where(Workout.id == workout_id)
        )
        return session.exec(statement).first()

# update an existing workout and optional endurance details atomically
def update_workout(
    workout: Workout,
    endurance_details: Optional[EnduranceDetails],
) -> Optional[Workout]:
    with Session(engine) as session:
        stored_workout = session.get(Workout, workout.id)
        if stored_workout is None:
            return None

        stored_workout.performed_at = workout.performed_at
        stored_workout.sport = workout.sport
        stored_workout.duration = workout.duration
        stored_workout.rpe = workout.rpe
        stored_workout.notes = workout.notes
        stored_workout.source = workout.source

        stored_details = session.get(EnduranceDetails, workout.id)
        if endurance_details is None and stored_details is not None:
            session.delete(stored_details)
        elif endurance_details is not None:
            if stored_details is None:
                endurance_details.workout_id = workout.id
                session.add(endurance_details)
            else:
                stored_details.distance = endurance_details.distance
                stored_details.elevation_gain = endurance_details.elevation_gain
                stored_details.average_hr = endurance_details.average_hr
                stored_details.max_hr = endurance_details.max_hr
                session.add(stored_details)

        session.add(stored_workout)
        session.commit()
        session.refresh(stored_workout)
        return stored_workout

# delete a workout and optional endurance details atomically
def delete_workout(workout_id: int) -> bool:
    with Session(engine) as session:
        workout = session.get(Workout, workout_id)
        if workout is None:
            return False

        endurance_details = session.get(EnduranceDetails, workout_id)
        if endurance_details is not None:
            session.delete(endurance_details)
        session.delete(workout)
        session.commit()
        return True

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

# persist a new planned workout
def save_planned_workout(planned_workout: PlannedWorkout) -> PlannedWorkout:
    with Session(engine) as session:
        session.add(planned_workout)
        session.commit()
        session.refresh(planned_workout)
        return planned_workout

# retrieve planned workouts inside an inclusive date range
def get_planned_workouts(
    start_at: datetime,
    end_at: datetime,
) -> list[PlannedWorkout]:
    with Session(engine) as session:
        statement = (
            select(PlannedWorkout)
            .where(PlannedWorkout.scheduled_at >= start_at)
            .where(PlannedWorkout.scheduled_at < end_at)
            .order_by(PlannedWorkout.scheduled_at, PlannedWorkout.id)
        )
        return list(session.exec(statement).all())

# retrieve a single planned workout by primary key
def get_planned_workout_by_id(
    planned_workout_id: int,
) -> Optional[PlannedWorkout]:
    with Session(engine) as session:
        return session.get(PlannedWorkout, planned_workout_id)

# update an existing planned workout without affecting completed workouts
def update_planned_workout(
    planned_workout: PlannedWorkout,
) -> Optional[PlannedWorkout]:
    with Session(engine) as session:
        stored_workout = session.get(PlannedWorkout, planned_workout.id)
        if stored_workout is None:
            return None

        stored_workout.scheduled_at = planned_workout.scheduled_at
        stored_workout.sport = planned_workout.sport
        stored_workout.workout_type = planned_workout.workout_type
        stored_workout.target_duration = planned_workout.target_duration
        stored_workout.target_distance = planned_workout.target_distance
        stored_workout.notes = planned_workout.notes
        stored_workout.status = planned_workout.status

        session.add(stored_workout)
        session.commit()
        session.refresh(stored_workout)
        return stored_workout

# delete one planned workout by primary key
def delete_planned_workout(planned_workout_id: int) -> bool:
    with Session(engine) as session:
        planned_workout = session.get(PlannedWorkout, planned_workout_id)
        if planned_workout is None:
            return False

        session.delete(planned_workout)
        session.commit()
        return True
