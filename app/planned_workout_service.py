"""Validation and orchestration for the athlete's weekly plan."""

from datetime import date, timedelta
from typing import Optional
from database import PlannedWorkout
from database import delete_planned_workout as remove_planned_workout
from database import get_planned_workouts, save_planned_workout
from database import update_planned_workout as persist_planned_workout_update
from workout_service import SUPPORTED_SPORTS

STATUS_PLANNED = "planned"
STATUS_COMPLETED = "completed"
STATUS_SKIPPED = "skipped"

PLANNED_WORKOUT_STATUSES = (
    STATUS_PLANNED,
    STATUS_COMPLETED,
    STATUS_SKIPPED,
)

# get the start and end dates for the calendar week containing the reference date
def get_week_range(reference_date: date) -> tuple[date, date]:
    week_start = reference_date - timedelta(days=reference_date.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end

# validate the fields for a planned workout
def validate_planned_workout(
    sport: str,
    workout_type: str,
    planned_duration: int,
    status: str,
) -> None:
    if sport not in SUPPORTED_SPORTS:
        raise ValueError("Choose a supported sport.")
    if not workout_type.strip():
        raise ValueError("Workout type cannot be empty.")
    if planned_duration <= 0:
        raise ValueError("Planned duration must be greater than zero.")
    if status not in PLANNED_WORKOUT_STATUSES:
        raise ValueError("Choose a valid planned workout status.")

# persist a new planned workout
def create_planned_workout(
    workout_date: date,
    sport: str,
    workout_type: str,
    planned_duration: int,
    notes: str,
    status: str = STATUS_PLANNED,
) -> PlannedWorkout:
    validate_planned_workout(sport, workout_type, planned_duration, status)
    planned_workout = PlannedWorkout(
        date=workout_date,
        sport=sport,
        workout_type=workout_type.strip(),
        planned_duration=planned_duration,
        notes=notes.strip() or None,
        status=status,
    )
    return save_planned_workout(planned_workout)

# return planned workouts for the reference date's calendar week
def get_weekly_plan(reference_date: date) -> list[PlannedWorkout]:
    week_start, week_end = get_week_range(reference_date)
    return get_planned_workouts(week_start, week_end)

# update an existing planned workout without affecting completed workouts
def edit_planned_workout(
    planned_workout_id: int,
    workout_date: date,
    sport: str,
    workout_type: str,
    planned_duration: int,
    notes: str,
    status: str,
) -> PlannedWorkout:
    validate_planned_workout(sport, workout_type, planned_duration, status)
    planned_workout = PlannedWorkout(
        id=planned_workout_id,
        date=workout_date,
        sport=sport,
        workout_type=workout_type.strip(),
        planned_duration=planned_duration,
        notes=notes.strip() or None,
        status=status,
    )
    updated_workout = persist_planned_workout_update(planned_workout)
    if updated_workout is None:
        raise ValueError("Planned workout not found.")
    return updated_workout

# delete an existing planned workout
def delete_planned_workout(planned_workout_id: int) -> None:
    if not remove_planned_workout(planned_workout_id):
        raise ValueError("Planned workout not found.")
