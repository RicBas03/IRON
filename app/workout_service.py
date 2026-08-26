from datetime import date
from typing import Optional
from database import EnduranceDetails, Workout, get_workouts, save_workout

SUPPORTED_SPORTS = ("Run", "Bike", "Swim", "Gym")
ENDURANCE_SPORTS = ("Run", "Bike", "Swim")

def log_workout(
    workout_date: date,
    sport: str,
    duration: int,
    rpe: int,
    notes: str,
    source: str = "manual",
    distance: Optional[float] = None,
    elevation_gain: Optional[float] = None,
    average_hr: Optional[int] = None,
    max_hr: Optional[int] = None,
) -> Workout:
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
        date=workout_date,
        sport=sport,
        duration=duration,
        rpe=rpe,
        notes=notes.strip() or None,
        source=source.strip(),
    )
    return save_workout(workout, endurance_details)

def get_workout_history() -> list[tuple[Workout, Optional[EnduranceDetails]]]:
    return get_workouts()
