"""Rule-based Decision Engine foundation for ranking workout candidates."""

from dataclasses import dataclass
from database import Goal
from planned_workout_service import (
    GYM_SPORT,
    MUSCLE_GROUPS,
    WORKOUT_TYPES_BY_SPORT,
)

# a candidate workout with its score and explainability details
@dataclass
class DecisionOption:
    sport: str
    workout_type: str
    score: float
    reasons: list[str]
    warnings: list[str]


# candidate definitions reuse the same canonical values as the Weekly Plan
CANDIDATE_WORKOUTS = tuple(
    (sport, workout_type)
    for sport, workout_types in WORKOUT_TYPES_BY_SPORT.items()
    for workout_type in workout_types
) + tuple((GYM_SPORT, muscle_group) for muscle_group in MUSCLE_GROUPS)

# goal-to-sport alignment for scoring candidates
GOAL_SPORT_ALIGNMENT = {
    "5K": ("Run",),
    "10K": ("Run",),
    "Half Marathon": ("Run",),
    "Marathon": ("Run",),
    "Half Ironman": ("Run", "Bike", "Swim"),
    "Ironman": ("Run", "Bike", "Swim"),
    "Cycling Performance": ("Bike",),
    "Swimming Performance": ("Swim",),
    "Muscle Gain": ("Gym",),
    "Strength Gain": ("Gym",),
    "Muscle Maintenance": ("Gym",),
    "Weight Loss": ("Run", "Bike", "Swim", "Gym"),
    "Body Recomposition": ("Run", "Bike", "Swim", "Gym"),
}

# generate workout candidates ranked only by active-goal alignment
def generate_candidate_options(active_goals: list[Goal]) -> list[DecisionOption]:
    goals = [goal for goal in active_goals if goal.active]
    options = []

    for sport, workout_type in CANDIDATE_WORKOUTS:
        score = 0.0
        reasons = []

        for goal in goals:
            aligned_sports = GOAL_SPORT_ALIGNMENT.get(goal.goal_type, ())
            if sport in aligned_sports:
                score += goal.priority
                reasons.append(
                    f"Aligned with {goal.goal_type} ({goal.priority}%)."
                )

        warnings = []
        if score == 0:
            warnings.append("No direct alignment with current active goals.")

        options.append(
            DecisionOption(
                sport=sport,
                workout_type=workout_type,
                score=score,
                reasons=reasons,
                warnings=warnings,
            )
        )

    return sorted(options, key=lambda option: option.score, reverse=True)


# return the highest-ranked candidates for display as recommendations
def get_recommended_options(
    active_goals: list[Goal],
    limit: int = 3,
) -> list[DecisionOption]:
    return generate_candidate_options(active_goals)[:limit]
