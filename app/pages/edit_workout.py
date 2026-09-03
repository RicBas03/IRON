"""Streamlit page for editing or deleting a selected calendar workout."""

from datetime import datetime
import streamlit as st
from database import create_db_and_tables
from planned_workout_service import (
    GYM_SPORT,
    MUSCLE_GROUPS,
    PLANNED_WORKOUT_STATUSES,
    WORKOUT_TYPES_BY_SPORT,
    delete_planned_workout,
    edit_planned_workout,
    get_planned_workout,
    get_selected_muscle_groups,
)
from workout_service import (
    ENDURANCE_SPORTS,
    SUPPORTED_SPORTS,
    delete_completed_workout,
    edit_completed_workout,
    get_completed_workout,
)

create_db_and_tables()

if st.button("← Weekly Plan"):
    st.switch_page("pages/weekly_plan.py")

st.title("Edit Workout")

workout_kind = st.session_state.get("selected_workout_kind")
workout_id = st.session_state.get("selected_workout_id")

if workout_kind not in ("planned", "completed") or workout_id is None:
    st.info("Select a workout from the Weekly Plan calendar.")
    st.stop()

if workout_kind == "planned":
    try:
        planned_workout = get_planned_workout(workout_id)
    except ValueError as error:
        st.error(str(error))
        st.stop()

    edited_sport = st.selectbox(
        "Sport",
        SUPPORTED_SPORTS,
        index=SUPPORTED_SPORTS.index(planned_workout.sport),
    )

    with st.form("edit_planned_workout_form"):
        edited_date = st.date_input(
            "Date",
            value=planned_workout.scheduled_at.date(),
        )
        edited_time = st.time_input(
            "Time",
            value=planned_workout.scheduled_at.time(),
            step=900,
        )

        if edited_sport == GYM_SPORT:
            default_muscle_groups = (
                get_selected_muscle_groups(planned_workout.workout_type)
                if planned_workout.sport == GYM_SPORT
                else []
            )
            muscle_groups = st.multiselect(
                "Muscle groups",
                MUSCLE_GROUPS,
                default=default_muscle_groups,
            )
            workout_type = ", ".join(muscle_groups)
        else:
            workout_type_options = WORKOUT_TYPES_BY_SPORT[edited_sport]
            current_workout_type = (
                planned_workout.workout_type
                if planned_workout.workout_type in workout_type_options
                else workout_type_options[0]
            )
            workout_type = st.selectbox(
                "Workout type",
                workout_type_options,
                index=workout_type_options.index(current_workout_type),
            )

        target_duration = st.number_input(
            "Target duration (minutes, optional)",
            min_value=1,
            value=planned_workout.target_duration,
            step=1,
        )

        if edited_sport == GYM_SPORT:
            target_distance = None
        else:
            distance_unit = "m" if edited_sport == "Swim" else "km"
            target_distance = st.number_input(
                f"Target distance ({distance_unit}, optional)",
                min_value=1.0 if edited_sport == "Swim" else 0.1,
                value=(
                    planned_workout.target_distance
                    if planned_workout.sport == edited_sport
                    else None
                ),
                step=50.0 if edited_sport == "Swim" else 0.1,
            )

        notes = st.text_area("Notes", value=planned_workout.notes or "")
        status = st.selectbox(
            "Status",
            PLANNED_WORKOUT_STATUSES,
            index=PLANNED_WORKOUT_STATUSES.index(planned_workout.status),
            format_func=str.title,
        )
        update_submitted = st.form_submit_button("Update workout")
        delete_submitted = st.form_submit_button("Delete workout")

    if delete_submitted:
        try:
            delete_planned_workout(workout_id)
        except ValueError as error:
            st.error(str(error))
        else:
            st.session_state["weekly_plan_feedback"] = "Planned workout deleted."
            st.switch_page("pages/weekly_plan.py")

    if update_submitted:
        try:
            edit_planned_workout(
                planned_workout_id=workout_id,
                workout_datetime=datetime.combine(edited_date, edited_time),
                sport=edited_sport,
                workout_type=workout_type,
                target_duration=target_duration,
                target_distance=target_distance,
                notes=notes,
                status=status,
            )
        except ValueError as error:
            st.error(str(error))
        else:
            st.session_state["weekly_plan_feedback"] = "Planned workout updated."
            st.switch_page("pages/weekly_plan.py")
else:
    try:
        completed_workout, endurance_details = get_completed_workout(workout_id)
    except ValueError as error:
        st.error(str(error))
        st.stop()

    edited_sport = st.selectbox(
        "Sport",
        SUPPORTED_SPORTS,
        index=SUPPORTED_SPORTS.index(completed_workout.sport),
    )

    with st.form("edit_completed_workout_form"):
        edited_date = st.date_input(
            "Date",
            value=completed_workout.performed_at.date(),
        )
        edited_time = st.time_input(
            "Time",
            value=completed_workout.performed_at.time(),
            step=900,
        )
        duration = st.number_input(
            "Duration (minutes)",
            min_value=1,
            value=completed_workout.duration,
            step=1,
        )
        rpe = st.slider(
            "RPE",
            min_value=1,
            max_value=10,
            value=completed_workout.rpe,
        )
        notes = st.text_area("Notes", value=completed_workout.notes or "")

        distance = None
        elevation_gain = None
        average_hr = None
        max_hr = None

        if edited_sport in ENDURANCE_SPORTS:
            same_endurance_sport = completed_workout.sport == edited_sport
            distance_unit = "m" if edited_sport == "Swim" else "km"
            distance = st.number_input(
                f"Distance ({distance_unit})",
                min_value=0.0,
                value=(
                    endurance_details.distance
                    if same_endurance_sport and endurance_details is not None
                    else 0.0
                ),
            )

            if edited_sport != "Swim":
                elevation_gain = st.number_input(
                    "Elevation gain (m)",
                    min_value=0.0,
                    value=(
                        endurance_details.elevation_gain
                        if same_endurance_sport and endurance_details is not None
                        else None
                    ),
                )

            average_hr = st.number_input(
                "Average heart rate (bpm)",
                min_value=1,
                step=1,
                value=(
                    endurance_details.average_hr
                    if same_endurance_sport and endurance_details is not None
                    else None
                ),
            )
            max_hr = st.number_input(
                "Maximum heart rate (bpm)",
                min_value=1,
                step=1,
                value=(
                    endurance_details.max_hr
                    if same_endurance_sport and endurance_details is not None
                    else None
                ),
            )

        update_submitted = st.form_submit_button("Update workout")
        delete_submitted = st.form_submit_button("Delete workout")

    if delete_submitted:
        try:
            delete_completed_workout(workout_id)
        except ValueError as error:
            st.error(str(error))
        else:
            st.session_state["weekly_plan_feedback"] = "Completed workout deleted."
            st.switch_page("pages/weekly_plan.py")

    if update_submitted:
        try:
            edit_completed_workout(
                workout_id=workout_id,
                workout_datetime=datetime.combine(edited_date, edited_time),
                sport=edited_sport,
                duration=duration,
                rpe=rpe,
                notes=notes,
                source=completed_workout.source,
                distance=distance,
                elevation_gain=elevation_gain,
                average_hr=average_hr,
                max_hr=max_hr,
            )
        except ValueError as error:
            st.error(str(error))
        else:
            st.session_state["weekly_plan_feedback"] = "Completed workout updated."
            st.switch_page("pages/weekly_plan.py")
