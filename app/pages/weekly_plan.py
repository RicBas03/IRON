"""Streamlit page for manually managing the athlete's weekly plan."""

from datetime import date, timedelta
import streamlit as st
from database import create_db_and_tables
from planned_workout_service import (
    GYM_SPORT,
    MUSCLE_GROUPS,
    PLANNED_WORKOUT_STATUSES,
    WORKOUT_TYPES_BY_SPORT,
    create_planned_workout,
    delete_planned_workout,
    edit_planned_workout,
    get_selected_muscle_groups,
    get_week_range,
    get_weekly_plan,
)
from workout_service import SUPPORTED_SPORTS

create_db_and_tables()

st.title("Weekly Plan")

# display feedback message from previous operation, if any
feedback_message = st.session_state.pop("weekly_plan_feedback", None)
if feedback_message is not None:
    st.success(feedback_message)

# change the week being displayed in the calendar
def change_week(days: int) -> None:
    st.session_state["weekly_plan_week_start"] += timedelta(days=days)
    st.session_state.pop("new_planned_workout_date", None)

# initialize the week being displayed in the calendar if not already set
if "weekly_plan_week_start" not in st.session_state:
    current_week_start, _ = get_week_range(date.today())
    st.session_state["weekly_plan_week_start"] = current_week_start

week_start = st.session_state["weekly_plan_week_start"]
week_end = week_start + timedelta(days=6)
planned_workouts = get_weekly_plan(week_start)

# render the calendar week with navigation buttons for previous and next weeks
previous_column, period_column, next_column = st.columns([1, 5, 1])
with previous_column:
    st.button(
        "←",
        help="Previous week",
        width="stretch",
        on_click=change_week,
        args=(-7,),
    )
with period_column:
    st.markdown(f"### {week_start:%d %b %Y} – {week_end:%d %b %Y}")
with next_column:
    st.button(
        "→",
        help="Next week",
        width="stretch",
        on_click=change_week,
        args=(7,),
    )

# group records once so each calendar column only renders its own day
workouts_by_date = {
    day: [workout for workout in planned_workouts if workout.date == day]
    for day in (week_start + timedelta(days=offset) for offset in range(7))
}

# render the calendar week with each day in its own column
calendar_columns = st.columns(7)
for day_offset, column in enumerate(calendar_columns):
    day = week_start + timedelta(days=day_offset)
    with column:
        st.markdown(f"**{day:%A}**")
        st.caption(f"{day:%d %b}")

        if not workouts_by_date[day]:
            st.caption("No workout")

        for planned_workout in workouts_by_date[day]:
            with st.container(border=True):
                st.write(f"**{planned_workout.sport}**")
                st.write(planned_workout.workout_type)
                targets = []
                if planned_workout.target_duration is not None:
                    targets.append(f"{planned_workout.target_duration} min")
                if planned_workout.target_distance is not None:
                    distance_unit = (
                        "m" if planned_workout.sport == "Swim" else "km"
                    )
                    targets.append(
                        f"{planned_workout.target_distance:g} {distance_unit}"
                    )
                targets.append(planned_workout.status.title())
                st.caption(" · ".join(targets))

st.subheader("Add planned workout")

new_sport = st.selectbox(
    "Sport",
    SUPPORTED_SPORTS,
    key="new_planned_workout_sport",
)

# render a form for adding a new planned workout
with st.form("add_planned_workout"):
    new_date = st.date_input(
        "Date",
        value=week_start,
        min_value=week_start,
        max_value=week_end,
        key="new_planned_workout_date",
    )

    if new_sport == GYM_SPORT:
        new_muscle_groups = st.multiselect(
            "Muscle groups",
            MUSCLE_GROUPS,
            key="new_planned_workout_muscle_groups",
        )
        new_workout_type = ", ".join(new_muscle_groups)
    else:
        new_workout_type = st.selectbox(
            "Workout type",
            WORKOUT_TYPES_BY_SPORT[new_sport],
            key=f"new_planned_workout_type_{new_sport}",
        )

    new_duration = st.number_input(
        "Target duration (minutes, optional)",
        min_value=1,
        value=None,
        step=1,
        key="new_planned_workout_target_duration",
    )

    if new_sport == GYM_SPORT:
        new_distance = None
    else:
        new_distance_unit = "m" if new_sport == "Swim" else "km"
        new_distance = st.number_input(
            f"Target distance ({new_distance_unit}, optional)",
            min_value=1.0 if new_sport == "Swim" else 0.1,
            value=None,
            step=50.0 if new_sport == "Swim" else 0.1,
            key=f"new_planned_workout_target_distance_{new_sport}",
        )

    new_notes = st.text_area("Notes", key="new_planned_workout_notes")
    new_status = st.selectbox(
        "Status",
        PLANNED_WORKOUT_STATUSES,
        format_func=str.title,
        key="new_planned_workout_status",
    )
    add_submitted = st.form_submit_button("Add workout")

# handle form submission for adding a new planned workout
if add_submitted:
    try:
        created_workout = create_planned_workout(
            workout_date=new_date,
            sport=new_sport,
            workout_type=new_workout_type,
            target_duration=new_duration,
            target_distance=new_distance,
            notes=new_notes,
            status=new_status,
        )
    except ValueError as error:
        st.error(str(error))
    else:
        st.session_state["weekly_plan_feedback"] = (
            f"Planned workout #{created_workout.id} added."
        )
        st.rerun()

st.subheader("Edit or delete")

# render a selectbox for choosing a planned workout to edit or delete
if planned_workouts:
    planned_workouts_by_id = {
        workout.id: workout
        for workout in planned_workouts
        if workout.id is not None
    }
    selected_workout_id = st.selectbox(
        "Planned workout",
        options=planned_workouts_by_id,
        format_func=lambda workout_id: (
            f"{planned_workouts_by_id[workout_id].date:%a %d %b} · "
            f"{planned_workouts_by_id[workout_id].sport} · "
            f"{planned_workouts_by_id[workout_id].workout_type}"
        ),
    )
    selected_workout = planned_workouts_by_id[selected_workout_id]

    edited_sport = st.selectbox(
        "Sport",
        SUPPORTED_SPORTS,
        index=SUPPORTED_SPORTS.index(selected_workout.sport),
        key=f"edited_sport_{selected_workout_id}",
    )

    # render a form for editing or deleting the selected planned workout
    with st.form(f"edit_planned_workout_{selected_workout_id}"):
        edited_date = st.date_input(
            "Date",
            value=selected_workout.date,
            key=f"edited_date_{selected_workout_id}",
        )

        if edited_sport == GYM_SPORT:
            default_muscle_groups = (
                get_selected_muscle_groups(selected_workout.workout_type)
                if selected_workout.sport == GYM_SPORT
                else []
            )
            edited_muscle_groups = st.multiselect(
                "Muscle groups",
                MUSCLE_GROUPS,
                default=default_muscle_groups,
                key=f"edited_muscle_groups_{selected_workout_id}",
            )
            edited_workout_type = ", ".join(edited_muscle_groups)
        else:
            workout_type_options = WORKOUT_TYPES_BY_SPORT[edited_sport]
            current_workout_type = (
                selected_workout.workout_type
                if selected_workout.workout_type in workout_type_options
                else workout_type_options[0]
            )
            edited_workout_type = st.selectbox(
                "Workout type",
                workout_type_options,
                index=workout_type_options.index(current_workout_type),
                key=f"edited_type_{selected_workout_id}_{edited_sport}",
            )

        edited_duration = st.number_input(
            "Target duration (minutes, optional)",
            min_value=1,
            value=selected_workout.target_duration,
            step=1,
            key=f"edited_target_duration_{selected_workout_id}",
        )

        if edited_sport == GYM_SPORT:
            edited_distance = None
        else:
            edited_distance_unit = "m" if edited_sport == "Swim" else "km"
            edited_distance = st.number_input(
                f"Target distance ({edited_distance_unit}, optional)",
                min_value=1.0 if edited_sport == "Swim" else 0.1,
                value=(
                    selected_workout.target_distance
                    if selected_workout.sport == edited_sport
                    else None
                ),
                step=50.0 if edited_sport == "Swim" else 0.1,
                key=f"edited_target_distance_{selected_workout_id}_{edited_sport}",
            )

        edited_notes = st.text_area(
            "Notes",
            value=selected_workout.notes or "",
            key=f"edited_notes_{selected_workout_id}",
        )
        edited_status = st.selectbox(
            "Status",
            PLANNED_WORKOUT_STATUSES,
            index=PLANNED_WORKOUT_STATUSES.index(selected_workout.status),
            format_func=str.title,
            key=f"edited_status_{selected_workout_id}",
        )

        update_submitted = st.form_submit_button("Update workout")
        delete_submitted = st.form_submit_button("Delete workout")

    # handle form submission for editing or deleting the selected planned workout
    if update_submitted:
        try:
            edit_planned_workout(
                planned_workout_id=selected_workout_id,
                workout_date=edited_date,
                sport=edited_sport,
                workout_type=edited_workout_type,
                target_duration=edited_duration,
                target_distance=edited_distance,
                notes=edited_notes,
                status=edited_status,
            )
        except ValueError as error:
            st.error(str(error))
        else:
            st.session_state["weekly_plan_feedback"] = "Planned workout updated."
            st.rerun()

    # handle form submission for deleting the selected planned workout
    if delete_submitted:
        try:
            delete_planned_workout(selected_workout_id)
        except ValueError as error:
            st.error(str(error))
        else:
            st.session_state["weekly_plan_feedback"] = "Planned workout deleted."
            st.rerun()
else:
    st.write("No planned workouts in this week.")
