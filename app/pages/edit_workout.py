"""Streamlit page for viewing and optionally editing a calendar workout."""

from datetime import datetime
import streamlit as st
from database import EnduranceDetails, PlannedWorkout, Workout, create_db_and_tables
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
    get_completed_workout_context,
)

# functions to display workout details
def show_planned_workout_details(planned_workout: PlannedWorkout) -> None:
    """Display all persisted information for a planned workout."""
    distance_unit = "m" if planned_workout.sport == "Swim" else "km"
    target_duration = (
        f"{planned_workout.target_duration} min"
        if planned_workout.target_duration is not None
        else "Not set"
    )
    target_distance = (
        f"{planned_workout.target_distance:g} {distance_unit}"
        if planned_workout.target_distance is not None
        else "Not set"
    )

    st.subheader("Planned workout")
    with st.container(border=True):
        st.write(f"**Sport:** {planned_workout.sport}")
        st.write(f"**Workout type:** {planned_workout.workout_type}")
        st.write(
            f"**Date and time:** "
            f"{planned_workout.scheduled_at:%A %d %B %Y at %H:%M}"
        )
        st.write(f"**Target duration:** {target_duration}")
        if planned_workout.sport != GYM_SPORT:
            st.write(f"**Target distance:** {target_distance}")
        st.write(f"**Status:** {planned_workout.status.title()}")
        st.write(f"**Notes:** {planned_workout.notes or '—'}")

# functions to display completed workout details
def show_completed_workout_details(
    workout: Workout,
    endurance_details: EnduranceDetails | None,
) -> None:
    """Display all persisted information for a completed workout."""
    st.subheader("Completed workout")
    with st.container(border=True):
        st.write(f"**Sport:** {workout.sport}")
        st.write(f"**Date and time:** {workout.performed_at:%A %d %B %Y at %H:%M}")
        st.write(f"**Duration:** {workout.duration} min")
        st.write(f"**RPE:** {workout.rpe}")

        if endurance_details is not None:
            distance_unit = "m" if workout.sport == "Swim" else "km"
            st.write(
                f"**Distance:** {endurance_details.distance:g} {distance_unit}"
            )
            if workout.sport != "Swim":
                elevation_gain = (
                    f"{endurance_details.elevation_gain:g} m"
                    if endurance_details.elevation_gain is not None
                    else "Not set"
                )
                st.write(f"**Elevation gain:** {elevation_gain}")
            st.write(
                f"**Average heart rate:** "
                f"{endurance_details.average_hr or 'Not set'}"
            )
            st.write(
                f"**Maximum heart rate:** "
                f"{endurance_details.max_hr or 'Not set'}"
            )

        st.write(f"**Notes:** {workout.notes or '—'}")
        st.write(f"**Source:** {workout.source}")

create_db_and_tables()

if st.button("← Weekly Plan"):
    st.session_state["workout_edit_mode"] = False
    st.switch_page("pages/weekly_plan.py")

st.title("Workout Details")

workout_kind = st.session_state.get("selected_workout_kind")
workout_id = st.session_state.get("selected_workout_id")
edit_mode = st.session_state.get("workout_edit_mode", False)

if workout_kind not in ("planned", "completed") or workout_id is None:
    st.info("Select a workout from the Weekly Plan calendar.")
    st.stop()

if workout_kind == "planned":
    try:
        planned_workout = get_planned_workout(workout_id)
    except ValueError as error:
        st.error(str(error))
        st.stop()

    if not edit_mode:
        show_planned_workout_details(planned_workout)
        if st.button("Edit"):
            st.session_state["workout_edit_mode"] = True
            st.rerun()
        st.stop()

    st.subheader("Edit details")
    if st.button("Cancel"):
        st.session_state["workout_edit_mode"] = False
        st.rerun()

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
            st.session_state["workout_edit_mode"] = False
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
            st.session_state["workout_edit_mode"] = False
            st.session_state["weekly_plan_feedback"] = "Planned workout updated."
            st.switch_page("pages/weekly_plan.py")
else:
    try:
        (
            completed_workout,
            endurance_details,
            linked_planned_workout,
        ) = get_completed_workout_context(workout_id)
    except ValueError as error:
        st.error(str(error))
        st.stop()

    if not edit_mode:
        show_completed_workout_details(completed_workout, endurance_details)
        if linked_planned_workout is not None:
            show_planned_workout_details(linked_planned_workout)
        if st.button("Edit"):
            st.session_state["workout_edit_mode"] = True
            st.rerun()
        st.stop()

    st.subheader("Edit details")
    if st.button("Cancel"):
        st.session_state["workout_edit_mode"] = False
        st.rerun()

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
            st.session_state["workout_edit_mode"] = False
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
            st.session_state["workout_edit_mode"] = False
            st.session_state["weekly_plan_feedback"] = "Completed workout updated."
            st.switch_page("pages/weekly_plan.py")
