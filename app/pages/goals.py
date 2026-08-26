"""Streamlit page for configuring the athlete's active goal set."""

import streamlit as st
from database import create_db_and_tables
from goal_service import (
    GOAL_CATEGORY_BY_TYPE,
    SUPPORTED_GOAL_TYPES,
    GoalInput,
    get_active_goals,
    save_active_goals,
)

create_db_and_tables()

st.title("Goals")

active_goals = get_active_goals()
active_goals_by_type = {goal.goal_type: goal for goal in active_goals}

# allow the user to select active goals and configure their priorities and target dates
selected_goal_types = st.multiselect(
    "Active goals",
    options=SUPPORTED_GOAL_TYPES,
    default=list(active_goals_by_type),
    format_func=lambda goal_type: (
        f"{GOAL_CATEGORY_BY_TYPE[goal_type]} — {goal_type}"
    ),
)

goal_inputs = []

# for each selected goal type, allow the user to configure its priority and target date
for goal_type in selected_goal_types:
    existing_goal = active_goals_by_type.get(goal_type)
    st.subheader(goal_type)

    priority = st.number_input(
        "Priority (%)",
        min_value=1,
        max_value=100,
        value=existing_goal.priority if existing_goal else 1,
        step=1,
        key=f"priority_{goal_type}",
    )
    target_date = st.date_input(
        "Target date (optional)",
        value=existing_goal.target_date if existing_goal else None,
        key=f"target_date_{goal_type}",
    )
    goal_inputs.append(
        GoalInput(
            goal_type=goal_type,
            priority=priority,
            target_date=target_date,
        )
    )

total_priority = sum(goal_input.priority for goal_input in goal_inputs)
st.metric("Total priority", f"{total_priority}%")

# validate the active goal set and provide feedback to the user
if selected_goal_types and total_priority == 100:
    st.success("Priorities add up to 100%. You can save the goals.")
else:
    st.warning("Active goal priorities must add up to exactly 100%.")

# allow the user to save the active goal set, which will be validated and persisted atomically
if st.button(
    "Save goals",
    disabled=not selected_goal_types or total_priority != 100,
):
    try:
        active_goals = save_active_goals(goal_inputs)
    except ValueError as error:
        st.error(str(error))
    else:
        st.success("Goals saved successfully.")

st.subheader("Saved active goals")

# display the saved active goals in a table, or show a message if there are no active goals
if active_goals:
    st.dataframe(
        [
            {
                "Goal": goal.goal_type,
                "Category": goal.category,
                "Priority": f"{goal.priority}%",
                "Target date": goal.target_date,
            }
            for goal in active_goals
        ],
        hide_index=True,
        width="stretch",
    )
else:
    st.write("No active goals saved yet.")
