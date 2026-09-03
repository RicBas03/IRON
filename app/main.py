"""Streamlit entrypoint and page navigation for IRON."""

import streamlit as st

st.set_page_config(page_title="IRON", layout="wide")

weekly_plan_page = st.Page("pages/weekly_plan.py", title="Weekly Plan")
goals_page = st.Page("pages/goals.py", title="Goals")
log_workout_page = st.Page("pages/log_workout.py", title="Log Workout")
edit_workout_page = st.Page("pages/edit_workout.py", title="Edit Workout")

navigation = st.navigation(
    [goals_page, weekly_plan_page, log_workout_page, edit_workout_page],
    position="hidden",
)

with st.sidebar:
    st.title("IRON")
    st.page_link(weekly_plan_page, width="stretch")
    st.page_link(goals_page, width="stretch")

navigation.run()
