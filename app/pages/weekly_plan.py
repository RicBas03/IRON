"""Streamlit page for managing planned and completed weekly workouts."""

from datetime import date, datetime, time, timedelta
import streamlit as st
from database import create_db_and_tables
from decision_engine import get_recommended_options
from goal_service import get_active_goals
from planned_workout_service import (
    create_planned_workout,
    get_week_range,
    get_weekly_plan,
)
from workout_service import get_completed_workouts_for_week

create_db_and_tables()

st.title("Weekly Plan")

# workout cards use keyed containers so styling remains scoped to the calendar
st.markdown(
    """
    <style>
    div[class*="st-key-calendar_card_"] button {
        min-height: 138px;
        padding: 0.9rem;
        justify-content: flex-start;
        text-align: left;
        white-space: normal;
        background: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.28);
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        transition: border-color 120ms ease, box-shadow 120ms ease,
            transform 120ms ease;
    }

    div[class*="st-key-calendar_card_"] button:hover {
        border-color: var(--primary-color);
        box-shadow: 0 5px 14px rgba(0, 0, 0, 0.14);
        transform: translateY(-1px);
    }

    div[class*="st-key-calendar_card_"] button p {
        width: 100%;
        text-align: left;
        line-height: 1.35;
    }

    div[class*="st-key-calendar_card_planned_"] button {
        border-left: 5px solid #4c8bf5;
    }

    div[class*="st-key-calendar_card_completed_"] button {
        border-left: 5px solid #21a366;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

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

calendar_title_column, add_workout_column = st.columns(
    [10, 1],
    vertical_alignment="center",
)
with calendar_title_column:
    st.subheader("Weekly calendar")
with add_workout_column:
    if st.button(
        "+",
        help="Add workout",
        width="stretch",
    ):
        st.switch_page("pages/log_workout.py")

# display the weekly calendar with planned and completed workouts
calendar_columns = st.columns(7, gap="small", border=True)
for day_offset, column in enumerate(calendar_columns):
    day = week_start + timedelta(days=day_offset)
    with column:
        with st.container(height=560):
            st.markdown(f"### {day:%A}")
            st.markdown(f"**{day:%d %B}**")
            st.divider()

            if not items_by_date[day]:
                st.write("No workout")

            for workout_datetime, entry_type, workout, details in items_by_date[day]:
                if entry_type == "planned":
                    workout_title = workout.workout_type
                    workout_details = []
                    if workout.target_duration is not None:
                        workout_details.append(f"{workout.target_duration} min")
                    if workout.target_distance is not None:
                        distance_unit = "m" if workout.sport == "Swim" else "km"
                        workout_details.append(
                            f"{workout.target_distance:g} {distance_unit}"
                        )
                    workout_details.append(workout.status.title())
                else:
                    workout_title = "Completed"
                    workout_details = [
                        f"{workout.duration} min",
                        f"RPE {workout.rpe}",
                    ]
                    if details is not None:
                        distance_unit = "m" if workout.sport == "Swim" else "km"
                        workout_details.append(
                            f"{details.distance:g} {distance_unit}"
                        )

                details_text = " · ".join(workout_details)
                card_label = (
                    f"**{workout_datetime:%H:%M}  ·  {workout.sport}**\n\n"
                    f"{workout_title}\n\n"
                    f"{details_text}"
                )

                with st.container(
                    key=f"calendar_card_{entry_type}_{workout.id}"
                ):
                    if st.button(
                        card_label,
                        key=f"open_{entry_type}_{workout.id}",
                        width="stretch",
                    ):
                        st.session_state["selected_workout_kind"] = entry_type
                        st.session_state["selected_workout_id"] = workout.id
                        st.switch_page("pages/edit_workout.py")

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
