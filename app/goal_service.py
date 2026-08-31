"""Goal catalog, validation rules, and persistence orchestration."""

from dataclasses import dataclass
from datetime import date
from typing import Optional
from database import Goal, get_active_goals as load_active_goals
from database import replace_active_goals

CATEGORY_ENDURANCE = "Endurance"
CATEGORY_STRENGTH_MUSCLE = "Strength / Muscle"
CATEGORY_BODY_COMPOSITION = "Body Composition"

# goal types are grouped into categories for display and validation purposes
GOAL_TYPES_BY_CATEGORY = {
    CATEGORY_ENDURANCE: (
        "5K",
        "10K",
        "Half Marathon",
        "Marathon",
        "Half Ironman",
        "Ironman",
        "Cycling Performance",
        "Swimming Performance",
    ),
    CATEGORY_STRENGTH_MUSCLE: (
        "Muscle Gain",
        "Strength Gain",
        "Muscle Maintenance",
    ),
    CATEGORY_BODY_COMPOSITION: (
        "Weight Loss",
        "Body Recomposition",
    ),
}

# map each goal type to its category for validation and persistence
GOAL_CATEGORY_BY_TYPE = {
    goal_type: category
    for category, goal_types in GOAL_TYPES_BY_CATEGORY.items()
    for goal_type in goal_types
}

SUPPORTED_GOAL_TYPES = tuple(GOAL_CATEGORY_BY_TYPE)

# define a dataclass for goal input, which is provider-independent and used to define one active goal
@dataclass(frozen=True)
class GoalInput:
    goal_type: str
    priority: int
    target_date: Optional[date] = None

# validate a complete active goal set before it is persisted
def validate_goal_inputs(goal_inputs: list[GoalInput]) -> None:
    if not goal_inputs:
        raise ValueError("Select at least one goal.")

    seen_goal_types = set()

    for goal_input in goal_inputs:
        if goal_input.goal_type not in GOAL_CATEGORY_BY_TYPE:
            raise ValueError(f"Unsupported goal: {goal_input.goal_type}.")
        if not 1 <= goal_input.priority <= 100:
            raise ValueError("Each priority must be between 1 and 100.")
        if goal_input.goal_type in seen_goal_types:
            raise ValueError("The same active goal cannot be selected twice.")

        seen_goal_types.add(goal_input.goal_type)

    total_priority = sum(goal_input.priority for goal_input in goal_inputs)
    if total_priority != 100:
        raise ValueError("Active goal priorities must add up to exactly 100%.")

# persist a validated active goal set atomically
def save_active_goals(goal_inputs: list[GoalInput]) -> list[Goal]:
    validate_goal_inputs(goal_inputs)

    goals = [
        Goal(
            goal_type=goal_input.goal_type,
            category=GOAL_CATEGORY_BY_TYPE[goal_input.goal_type],
            priority=goal_input.priority,
            target_date=goal_input.target_date,
            active=True,
        )
        for goal_input in goal_inputs
    ]
    return replace_active_goals(goals)

# expose active goals through the service layer
def get_active_goals() -> list[Goal]:
    return load_active_goals()
