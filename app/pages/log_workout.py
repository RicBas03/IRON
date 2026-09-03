"""Streamlit page for adding a planned or completed workout."""

from datetime import date, datetime, time, timedelta
import streamlit as st
from database import create_db_and_tables
from planned_workout_service import (
    GYM_SPORT,
    MUSCLE_GROUPS,
    WORKOUT_TYPES_BY_SPORT,
    create_planned_workout,
    get_week_range,
)
from workout_service import (
    ENDURANCE_SPORTS,
    ENTRY_COMPLETED,
    SUPPORTED_SPORTS,
    classify_workout_datetime,
    log_workout,
)

create_db_and_tables()

if st.button("← Weekly Plan"):
    st.switch_page("pages/weekly_plan.py")

st.title("Log Workout")

if "weekly_plan_week_start" not in st.session_state:
    current_week_start, _ = get_week_range(date.today())
    st.session_state["weekly_plan_week_start"] = current_week_start

week_start = st.session_state["weekly_plan_week_start"]
week_end = week_start + timedelta(days=6)
current_datetime = datetime.now()
default_entry_date = (
    date.today() if week_start <= date.today() <= week_end else week_start
)

entry_date = st.date_input(
    "Date",
    value=default_entry_date,
    min_value=week_start,
    max_value=week_end,
)
entry_time = st.time_input("Time", value=time(18, 0), step=900)
entry_datetime = datetime.combine(entry_date, entry_time)
entry_type = classify_workout_datetime(entry_datetime, current_datetime)
entry_sport = st.selectbox("Sport", SUPPORTED_SPORTS)

if entry_type == ENTRY_COMPLETED:
    st.info("The selected time is in the past: log a completed workout.")

    with st.form("completed_workout_form"):
        duration = st.number_input(
            "Duration (minutes)",
            min_value=1,
            step=1,
        )
        rpe = st.slider("RPE", min_value=1, max_value=10)
        notes = st.text_area("Notes")

        distance = None
        elevation_gain = None
        average_hr = None
        max_hr = None

        if entry_sport in ENDURANCE_SPORTS:
            distance_unit = "m" if entry_sport == "Swim" else "km"
            distance = st.number_input(
                f"Distance ({distance_unit})",
                min_value=0.0,
            )

            if entry_sport != "Swim":
                elevation_gain = st.number_input(
                    "Elevation gain (m)",
                    min_value=0.0,
                    value=None,
                )

            average_hr = st.number_input(
                "Average heart rate (bpm)",
                min_value=1,
                step=1,
                value=None,
            )
            max_hr = st.number_input(
                "Maximum heart rate (bpm)",
                min_value=1,
                step=1,
                value=None,
            )

        submitted = st.form_submit_button("Save completed workout")

    if submitted:
        try:
            workout = log_workout(
                workout_datetime=entry_datetime,
                sport=entry_sport,
                duration=duration,
                rpe=rpe,
                notes=notes,
                distance=distance,
                elevation_gain=elevation_gain,
                average_hr=average_hr,
                max_hr=max_hr,
            )
        except ValueError as error:
            st.error(str(error))
        else:
            st.session_state["weekly_plan_feedback"] = (
                f"Completed workout #{workout.id} saved."
            )
            st.switch_page("pages/weekly_plan.py")
else:
    st.info("The selected time is in the future: add a planned workout.")

    with st.form("planned_workout_form"):
        if entry_sport == GYM_SPORT:
            muscle_groups = st.multiselect("Muscle groups", MUSCLE_GROUPS)
            workout_type = ", ".join(muscle_groups)
        else:
            workout_type = st.selectbox(
                "Workout type",
                WORKOUT_TYPES_BY_SPORT[entry_sport],
            )

        target_duration = st.number_input(
            "Target duration (minutes, optional)",
            min_value=1,
            value=None,
            step=1,
        )

        if entry_sport == GYM_SPORT:
            target_distance = None
        else:
            distance_unit = "m" if entry_sport == "Swim" else "km"
            target_distance = st.number_input(
                f"Target distance ({distance_unit}, optional)",
                min_value=1.0 if entry_sport == "Swim" else 0.1,
                value=None,
                step=50.0 if entry_sport == "Swim" else 0.1,
            )

        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Add planned workout")

    if submitted:
        try:
            planned_workout = create_planned_workout(
                workout_datetime=entry_datetime,
                sport=entry_sport,
                workout_type=workout_type,
                target_duration=target_duration,
                target_distance=target_distance,
                notes=notes,
            )
        except ValueError as error:
            st.error(str(error))
        else:
            st.session_state["weekly_plan_feedback"] = (
                f"Planned workout #{planned_workout.id} added."
            )
            st.switch_page("pages/weekly_plan.py")
