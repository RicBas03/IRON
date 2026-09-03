"""Validation and orchestration for completed workout operations."""

from datetime import date, datetime, time, timedelta
from typing import Optional
from database import EnduranceDetails, Workout, get_workouts, save_workout
from database import delete_workout as remove_workout
from database import get_workout_by_id
from database import update_workout as persist_workout_update

SUPPORTED_SPORTS = ("Run", "Bike", "Swim", "Gym")
ENDURANCE_SPORTS = ("Run", "Bike", "Swim")
ENTRY_COMPLETED = "completed"
ENTRY_PLANNED = "planned"

# classify a workout entry as completed or planned based on its datetime
def classify_workout_datetime(
    workout_datetime: datetime,
    current_datetime: Optional[datetime] = None,
) -> str:
    reference_datetime = current_datetime or datetime.now()
    if workout_datetime < reference_datetime:
        return ENTRY_COMPLETED
    return ENTRY_PLANNED

# validate and persist a completed workout record, including optional endurance metadata
def _build_completed_workout(
    workout_datetime: datetime,
    sport: str,
    duration: int,
    rpe: int,
    notes: str,
    source: str = "manual",
    distance: Optional[float] = None,
    elevation_gain: Optional[float] = None,
    average_hr: Optional[int] = None,
    max_hr: Optional[int] = None,
    workout_id: Optional[int] = None,
) -> tuple[Workout, Optional[EnduranceDetails]]:
    if sport not in SUPPORTED_SPORTS:
        raise ValueError("Choose a supported sport.")
    if duration <= 0:
        raise ValueError("Duration must be greater than zero.")
    if not 1 <= rpe <= 10:
        raise ValueError("RPE must be between 1 and 10.")
    if not source.strip():
        raise ValueError("Source cannot be empty.")

    endurance_values = (
        distance,
        elevation_gain,
        average_hr,
        max_hr,
    )
    endurance_details = None

    # validate endurance details if the sport is an endurance sport
    if sport in ENDURANCE_SPORTS:
        if distance is None or distance <= 0:
            raise ValueError("Distance must be greater than zero.")
        if sport == "Swim" and elevation_gain is not None:
            raise ValueError("Elevation gain is not valid for Swim.")
        if elevation_gain is not None and elevation_gain < 0:
            raise ValueError("Elevation gain cannot be negative.")
        if average_hr is not None and average_hr <= 0:
            raise ValueError("Average heart rate must be greater than zero.")
        if max_hr is not None and max_hr <= 0:
            raise ValueError("Maximum heart rate must be greater than zero.")
        if average_hr is not None and max_hr is not None and average_hr > max_hr:
            raise ValueError("Average heart rate cannot exceed maximum heart rate.")

        endurance_details = EnduranceDetails(
            distance=distance,
            elevation_gain=elevation_gain,
            average_hr=average_hr,
            max_hr=max_hr,
        )
    elif any(value is not None for value in endurance_values):
        raise ValueError("Endurance details are only valid for Run, Bike, and Swim.")

    workout = Workout(
        id=workout_id,
        performed_at=workout_datetime,
        sport=sport,
        duration=duration,
        rpe=rpe,
        notes=notes.strip() or None,
        source=source.strip(),
    )
    return workout, endurance_details

# validate and persist a workout record, including optional endurance metadata
def log_workout(
    workout_datetime: datetime,
    sport: str,
    duration: int,
    rpe: int,
    notes: str,
    source: str = "manual",
    distance: Optional[float] = None,
    elevation_gain: Optional[float] = None,
    average_hr: Optional[int] = None,
    max_hr: Optional[int] = None,
    current_datetime: Optional[datetime] = None,
) -> Workout:
    if (
        classify_workout_datetime(workout_datetime, current_datetime)
        != ENTRY_COMPLETED
    ):
        raise ValueError("A completed workout must be in the past.")
    workout, endurance_details = _build_completed_workout(
        workout_datetime=workout_datetime,
        sport=sport,
        duration=duration,
        rpe=rpe,
        notes=notes,
        source=source,
        distance=distance,
        elevation_gain=elevation_gain,
        average_hr=average_hr,
        max_hr=max_hr,
    )
    return save_workout(workout, endurance_details)

# expose completed workouts for a given week without leaking persistence into the UI
def get_completed_workout(
    workout_id: int,
) -> tuple[Workout, Optional[EnduranceDetails]]:
    workout_record = get_workout_by_id(workout_id)
    if workout_record is None:
        raise ValueError("Completed workout not found.")
    return workout_record

# update an existing completed workout record, including optional endurance metadata
def edit_completed_workout(
    workout_id: int,
    workout_datetime: datetime,
    sport: str,
    duration: int,
    rpe: int,
    notes: str,
    source: str = "manual",
    distance: Optional[float] = None,
    elevation_gain: Optional[float] = None,
    average_hr: Optional[int] = None,
    max_hr: Optional[int] = None,
    current_datetime: Optional[datetime] = None,
) -> Workout:
    if (
        classify_workout_datetime(workout_datetime, current_datetime)
        != ENTRY_COMPLETED
    ):
        raise ValueError("A completed workout must be in the past.")
    workout, endurance_details = _build_completed_workout(
        workout_id=workout_id,
        workout_datetime=workout_datetime,
        sport=sport,
        duration=duration,
        rpe=rpe,
        notes=notes,
        source=source,
        distance=distance,
        elevation_gain=elevation_gain,
        average_hr=average_hr,
        max_hr=max_hr,
    )
    updated_workout = persist_workout_update(workout, endurance_details)
    if updated_workout is None:
        raise ValueError("Completed workout not found.")
    return updated_workout

# delete a completed workout record, including optional endurance metadata
def delete_completed_workout(workout_id: int) -> None:
    if not remove_workout(workout_id):
        raise ValueError("Completed workout not found.")

# expose workout history without leaking persistence into the UI
def get_workout_history() -> list[tuple[Workout, Optional[EnduranceDetails]]]:
    return get_workouts()

# expose completed workouts for a given week without leaking persistence into the UI
def get_completed_workouts_for_week(
    reference_date: date,
) -> list[tuple[Workout, Optional[EnduranceDetails]]]:
    week_start = reference_date - timedelta(days=reference_date.weekday())
    start_at = datetime.combine(week_start, time.min)
    end_at = start_at + timedelta(days=7)
    return get_workouts(start_at, end_at)
