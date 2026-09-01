"""Validation and orchestration for the athlete's weekly plan."""

from datetime import date, datetime, time, timedelta
from typing import Optional
from database import PlannedWorkout
from database import delete_planned_workout as remove_planned_workout
from database import get_planned_workouts, save_planned_workout
from database import update_planned_workout as persist_planned_workout_update
from workout_service import (
    ENTRY_PLANNED,
    SUPPORTED_SPORTS,
    classify_workout_datetime,
)

STATUS_PLANNED = "planned"
STATUS_SKIPPED = "skipped"

PLANNED_WORKOUT_STATUSES = (
    STATUS_PLANNED,
    STATUS_SKIPPED,
)

GYM_SPORT = "Gym"

# supported workout types for each sport
WORKOUT_TYPES_BY_SPORT = {
    "Run": (
        "Easy Run",
        "Long Run",
        "Recovery Run",
        "Tempo Run",
        "Intervals",
        "Progressive Run",
    ),
    "Bike": (
        "Easy Ride",
        "Long Ride",
        "Intervals",
    ),
    "Swim": (
        "Easy Swim",
        "Endurance Swim",
        "Intervals",
        "Technique",
    ),
}

MUSCLE_GROUPS = (
    "Chest",
    "Back",
    "Shoulders",
    "Biceps",
    "Triceps",
    "Quadriceps",
    "Hamstrings",
    "Glutes",
    "Calves",
    "Core",
)

# return recognized muscle groups in their canonical order
def get_selected_muscle_groups(workout_type: str) -> list[str]:
    selected_names = {
        muscle_group.strip().casefold()
        for muscle_group in workout_type.split(",")
        if muscle_group.strip()
    }
    return [
        muscle_group
        for muscle_group in MUSCLE_GROUPS
        if muscle_group.casefold() in selected_names
    ]

# validate a sport-specific type and return its canonical value
def normalize_workout_type(sport: str, workout_type: str) -> str:
    if sport == GYM_SPORT:
        requested_groups = [
            muscle_group.strip()
            for muscle_group in workout_type.split(",")
            if muscle_group.strip()
        ]
        normalized_groups = get_selected_muscle_groups(workout_type)

        if not requested_groups:
            raise ValueError("Select at least one muscle group.")
        if len({group.casefold() for group in requested_groups}) != len(
            requested_groups
        ):
            raise ValueError("A muscle group cannot be selected twice.")
        if len(normalized_groups) != len(requested_groups):
            raise ValueError("Choose only supported muscle groups.")

        return ", ".join(normalized_groups)

    supported_types = WORKOUT_TYPES_BY_SPORT.get(sport)
    if supported_types is None:
        raise ValueError("Choose a supported sport.")

    normalized_types = {
        supported_type.casefold(): supported_type
        for supported_type in supported_types
    }
    normalized_workout_type = normalized_types.get(workout_type.strip().casefold())
    if normalized_workout_type is None:
        raise ValueError(f"Choose a supported workout type for {sport}.")
    return normalized_workout_type

# get the start and end dates for the calendar week containing the reference date
def get_week_range(reference_date: date) -> tuple[date, date]:
    week_start = reference_date - timedelta(days=reference_date.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end

# validate the fields for a planned workout
def validate_planned_workout(
    sport: str,
    workout_type: str,
    target_duration: Optional[int],
    target_distance: Optional[float],
    status: str,
) -> str:
    if sport not in SUPPORTED_SPORTS:
        raise ValueError("Choose a supported sport.")
    normalized_workout_type = normalize_workout_type(sport, workout_type)
    if target_duration is not None and target_duration <= 0:
        raise ValueError("Target duration must be greater than zero.")
    if target_distance is not None and target_distance <= 0:
        raise ValueError("Target distance must be greater than zero.")
    if sport == GYM_SPORT and target_distance is not None:
        raise ValueError("Target distance is not valid for Gym.")
    if status not in PLANNED_WORKOUT_STATUSES:
        raise ValueError("Choose a valid planned workout status.")
    return normalized_workout_type

# persist a new planned workout
def create_planned_workout(
    workout_datetime: datetime,
    sport: str,
    workout_type: str,
    target_duration: Optional[int],
    target_distance: Optional[float],
    notes: str,
    current_datetime: Optional[datetime] = None,
) -> PlannedWorkout:
    if (
        classify_workout_datetime(workout_datetime, current_datetime)
        != ENTRY_PLANNED
    ):
        raise ValueError("A planned workout must be in the future.")
    normalized_workout_type = validate_planned_workout(
        sport,
        workout_type,
        target_duration,
        target_distance,
        STATUS_PLANNED,
    )
    planned_workout = PlannedWorkout(
        scheduled_at=workout_datetime,
        sport=sport,
        workout_type=normalized_workout_type,
        target_duration=target_duration,
        target_distance=target_distance,
        notes=notes.strip() or None,
        status=STATUS_PLANNED,
    )
    return save_planned_workout(planned_workout)

# return planned workouts for the reference date's calendar week
def get_weekly_plan(reference_date: date) -> list[PlannedWorkout]:
    week_start, _ = get_week_range(reference_date)
    start_at = datetime.combine(week_start, time.min)
    end_at = start_at + timedelta(days=7)
    return get_planned_workouts(start_at, end_at)

# update an existing planned workout without affecting completed workouts
def edit_planned_workout(
    planned_workout_id: int,
    workout_datetime: datetime,
    sport: str,
    workout_type: str,
    target_duration: Optional[int],
    target_distance: Optional[float],
    notes: str,
    status: str,
    current_datetime: Optional[datetime] = None,
) -> PlannedWorkout:
    if (
        status == STATUS_PLANNED
        and classify_workout_datetime(workout_datetime, current_datetime)
        != ENTRY_PLANNED
    ):
        raise ValueError("A planned workout must be in the future.")
    normalized_workout_type = validate_planned_workout(
        sport,
        workout_type,
        target_duration,
        target_distance,
        status,
    )
    planned_workout = PlannedWorkout(
        id=planned_workout_id,
        scheduled_at=workout_datetime,
        sport=sport,
        workout_type=normalized_workout_type,
        target_duration=target_duration,
        target_distance=target_distance,
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
