import streamlit as st
from database import create_db_and_tables
from workout_service import (
    ENDURANCE_SPORTS,
    SUPPORTED_SPORTS,
    get_workout_history,
    log_workout,
)

create_db_and_tables()

st.title("IRON")
st.subheader("Log workout")

sport = st.selectbox("Sport", SUPPORTED_SPORTS)

with st.form("workout_form"):
    workout_date = st.date_input("Date")
    duration = st.number_input("Duration (minutes)", min_value=0, step=1)
    rpe = st.slider("RPE", min_value=1, max_value=10)
    notes = st.text_area("Notes")

    distance = None
    elevation_gain = None
    average_hr = None
    max_hr = None
    cadence = None

    if sport in ENDURANCE_SPORTS:
        distance_unit = "m" if sport == "Swim" else "km"
        distance = st.number_input(f"Distance ({distance_unit})", min_value=0.0)

        if sport != "Swim":
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

    submitted = st.form_submit_button("Save workout")

if submitted:
    try:
        workout = log_workout(
            workout_date=workout_date,
            sport=sport,
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
        st.success(f"Workout #{workout.id} saved!")

st.subheader("Workout history")

workouts = get_workout_history()

if workouts:
    st.dataframe(
        [
            {
                "Date": workout.date,
                "Sport": workout.sport,
                "Duration (minutes)": workout.duration,
                "Distance": (
                    f"{details.distance:g} {'m' if workout.sport == 'Swim' else 'km'}"
                    if details
                    else None
                ),
                "Elevation gain (m)": details.elevation_gain if details else None,
                "Average HR": details.average_hr if details else None,
                "Maximum HR": details.max_hr if details else None,
                "RPE": workout.rpe,
                "Source": workout.source,
                "Notes": workout.notes or "",
            }
            for workout, details in workouts
        ],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.write("No workouts logged yet.")
