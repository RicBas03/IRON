"""Streamlit entrypoint and page navigation for IRON."""

import streamlit as st

st.set_page_config(page_title="IRON")

weekly_plan_page = st.Page("pages/weekly_plan.py", title="Weekly Plan")
log_workout_page = st.Page("pages/log_workout.py", title="Log Workout")
goals_page = st.Page("pages/goals.py", title="Goals")

navigation = st.navigation(
    [log_workout_page, goals_page, weekly_plan_page],
    position="hidden",
)

with st.sidebar:
    st.title("IRON")
    st.page_link(weekly_plan_page, width="stretch")
    st.page_link(log_workout_page, width="stretch")
    st.page_link(goals_page, width="stretch")

navigation.run()
