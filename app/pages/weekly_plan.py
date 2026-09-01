"""Streamlit page for managing planned and completed weekly workouts."""

from datetime import date, datetime, time, timedelta
import streamlit as st
from database import create_db_and_tables
from decision_engine import get_recommended_options
from goal_service import get_active_goals
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
from workout_service import (
    ENDURANCE_SPORTS,
    ENTRY_COMPLETED,
    SUPPORTED_SPORTS,
    classify_workout_datetime,
    get_completed_workouts_for_week,
    log_workout,
)

create_db_and_tables()

st.title("Weekly Plan")

feedback_message = st.session_state.pop("weekly_plan_feedback", None)
if feedback_message is not None:
    st.success(feedback_message)

# allow the user to navigate between weeks
def change_week(days: int) -> None:
    st.session_state["weekly_plan_week_start"] += timedelta(days=days)

# initialize the week start date in session state if not already set
if "weekly_plan_week_start" not in st.session_state:
    current_week_start, _ = get_week_range(date.today())
    st.session_state["weekly_plan_week_start"] = current_week_start

week_start = st.session_state["weekly_plan_week_start"]
week_end = week_start + timedelta(days=6)
current_datetime = datetime.now()
planned_workouts = get_weekly_plan(week_start)
completed_workouts = get_completed_workouts_for_week(week_start)
active_goals = get_active_goals()
recommended_options = get_recommended_options(active_goals)

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

calendar_items = [
    (planned_workout.scheduled_at, "planned", planned_workout, None)
    for planned_workout in planned_workouts
] + [
    (workout.performed_at, "completed", workout, details)
    for workout, details in completed_workouts
]
calendar_items.sort(key=lambda item: item[0])

items_by_date = {
    day: [item for item in calendar_items if item[0].date() == day]
    for day in (week_start + timedelta(days=offset) for offset in range(7))
}

# display the weekly calendar with planned and completed workouts
calendar_columns = st.columns(7)
for day_offset, column in enumerate(calendar_columns):
    day = week_start + timedelta(days=day_offset)
    with column:
        st.markdown(f"**{day:%A}**")
        st.caption(f"{day:%d %b}")

        if not items_by_date[day]:
            st.caption("No workout")

        for workout_datetime, entry_type, workout, details in items_by_date[day]:
            with st.container(border=True):
                st.write(f"**{workout.sport}**")
                st.caption(workout_datetime.strftime("%H:%M"))

                if entry_type == "planned":
                    st.write(workout.workout_type)
                    targets = []
                    if workout.target_duration is not None:
                        targets.append(f"{workout.target_duration} min")
                    if workout.target_distance is not None:
                        distance_unit = "m" if workout.sport == "Swim" else "km"
                        targets.append(
                            f"{workout.target_distance:g} {distance_unit}"
                        )
                    targets.append(workout.status.title())
                    st.caption(" · ".join(targets))
                else:
                    st.write("Completed")
                    actual_values = [f"{workout.duration} min", f"RPE {workout.rpe}"]
                    if details is not None:
                        distance_unit = "m" if workout.sport == "Swim" else "km"
                        actual_values.append(
                            f"{details.distance:g} {distance_unit}"
                        )
                    st.caption(" · ".join(actual_values))

st.subheader("Recommended workouts")

future_week_days = tuple(
    day
    for day in (week_start + timedelta(days=offset) for offset in range(7))
    if datetime.combine(day, time.max) >= current_datetime
)

# display recommended workouts for the week if there are active goals and future days
if active_goals and future_week_days:
    recommendation_columns = st.columns(3)
    default_recommendation_date = next(
        (
            day
            for day in future_week_days
            if datetime.combine(day, time(18, 0)) >= current_datetime
        ),
        future_week_days[-1],
    )

    for index, (column, option) in enumerate(
        zip(recommendation_columns, recommended_options)
    ):
        with column:
            with st.container(border=True):
                st.write(f"**{option.sport}**")
                st.write(option.workout_type)
                st.caption(f"Goal alignment: {option.score:g}%")
                for reason in option.reasons:
                    st.caption(reason)

                recommended_date = st.selectbox(
                    "Date",
                    future_week_days,
                    index=future_week_days.index(default_recommendation_date),
                    format_func=lambda selected_date: selected_date.strftime(
                        "%A %d %b"
                    ),
                    key=f"recommendation_date_{week_start}_{index}",
                )
                recommended_time = st.time_input(
                    "Time",
                    value=time(18, 0),
                    step=900,
                    key=f"recommendation_time_{week_start}_{index}",
                )

                if st.button(
                    "Add to plan",
                    key=f"add_recommendation_{week_start}_{index}",
                    width="stretch",
                ):
                    try:
                        create_planned_workout(
                            workout_datetime=datetime.combine(
                                recommended_date,
                                recommended_time,
                            ),
                            sport=option.sport,
                            workout_type=option.workout_type,
                            target_duration=None,
                            target_distance=None,
                            notes="",
                        )
                    except ValueError as error:
                        st.error(str(error))
                    else:
                        st.session_state["weekly_plan_feedback"] = (
                            f"Recommended {option.sport} workout added."
                        )
                        st.rerun()
elif not active_goals:
    st.info("Save active goals to receive workout recommendations.")
else:
    st.info("This week has no future dates for workout recommendations.")

st.subheader("Add workout")

# allow the user to add a planned or completed workout for the week
default_entry_date = (
    date.today() if week_start <= date.today() <= week_end else week_start
)
entry_date = st.date_input(
    "Date",
    value=default_entry_date,
    min_value=week_start,
    max_value=week_end,
    key=f"workout_entry_date_{week_start}",
)
entry_time = st.time_input(
    "Time",
    value=time(18, 0),
    step=900,
    key=f"workout_entry_time_{week_start}",
)
entry_datetime = datetime.combine(entry_date, entry_time)
entry_type = classify_workout_datetime(entry_datetime, current_datetime)
entry_sport = st.selectbox(
    "Sport",
    SUPPORTED_SPORTS,
    key="workout_entry_sport",
)

# display the appropriate form based on whether the workout is planned or completed
if entry_type == ENTRY_COMPLETED:
    st.caption("The selected time is in the past: log a completed workout.")

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

        completed_submitted = st.form_submit_button("Save completed workout")

    if completed_submitted:
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
            st.rerun()
else:
    st.caption("The selected time is in the future: add a planned workout.")

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

        planned_notes = st.text_area("Notes")
        planned_submitted = st.form_submit_button("Add planned workout")

    if planned_submitted:
        try:
            planned_workout = create_planned_workout(
                workout_datetime=entry_datetime,
                sport=entry_sport,
                workout_type=workout_type,
                target_duration=target_duration,
                target_distance=target_distance,
                notes=planned_notes,
            )
        except ValueError as error:
            st.error(str(error))
        else:
            st.session_state["weekly_plan_feedback"] = (
                f"Planned workout #{planned_workout.id} added."
            )
            st.rerun()

st.subheader("Edit or delete planned workout")

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
            f"{planned_workouts_by_id[workout_id].scheduled_at:%a %d %b %H:%M} · "
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

    with st.form(f"edit_planned_workout_{selected_workout_id}"):
        edited_date = st.date_input(
            "Date",
            value=selected_workout.scheduled_at.date(),
            key=f"edited_date_{selected_workout_id}",
        )
        edited_time = st.time_input(
            "Time",
            value=selected_workout.scheduled_at.time(),
            step=900,
            key=f"edited_time_{selected_workout_id}",
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

    if update_submitted:
        try:
            edit_planned_workout(
                planned_workout_id=selected_workout_id,
                workout_datetime=datetime.combine(edited_date, edited_time),
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
