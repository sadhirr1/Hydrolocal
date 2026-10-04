"""HydroLocal - a private hydration coach that runs on your own computer.

The schedule numbers come from hydration.py. The explanation is written by an
open-weight model (Gemma) running locally in LM Studio. Nothing is sent to the
internet and nothing is saved.
"""
from datetime import datetime, time

import pandas as pd
import streamlit as st

import hydration as hy
import llm

st.set_page_config(page_title="HydroLocal", page_icon="💧", layout="wide")

SAFETY = (
    "HydroLocal gives general hydration guidance only. It is not medical advice and "
    "it can't tell you why someone feels unwell. If you or anyone feels dizzy, faint, "
    "confused or very unwell: stop, sit down, tell someone nearby and get medical help. "
    "People with kidney, heart or other medical conditions should follow their doctor's "
    "advice about fluids."
)

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Local AI")
    base_url = st.text_input("LM Studio address", llm.DEFAULT_BASE_URL)
    model_name = st.text_input("Model name (leave empty to auto-detect)", "")
    use_ai = st.toggle("Write an AI explanation", value=True)
    st.caption("Runs on this computer through LM Studio. No data leaves your machine.")
    st.divider()
    weight_kg = st.number_input("Body weight (kg)", 30.0, 200.0, 70.0, 1.0)
    st.caption("Used only to scale the numbers. Never stored.")

st.title("💧 HydroLocal")
st.write("A private hydration coach that runs on your own laptop.")
st.info(SAFETY)

tab_shift, tab_daily, tab_trek = st.tabs(
    ["Shift at work", "Everyday reminders", "Trek pacing"]
)
today = datetime.now().date()


def at(t: time) -> datetime:
    return datetime.combine(today, t)


def show(plan: hy.Plan, context: str, key: str) -> None:
    """Render a plan: metric cards, schedule table, AI note, calendar download."""
    if not plan.events:
        for w in plan.warnings:
            st.warning(w)
        return

    cols = st.columns(max(1, len(plan.headline)))
    for col, (label, value) in zip(cols, plan.headline.items()):
        col.metric(label, value)

    for w in plan.warnings:
        st.warning(w)

    df = pd.DataFrame(
        {
            "Time": [e.when.strftime("%H:%M") for e in plan.events],
            "Drink": [f"{e.ml} ml" for e in plan.events],
            "What": [e.label for e in plan.events],
        }
    )
    st.subheader("Your schedule")
    st.dataframe(df, hide_index=True, use_container_width=True)

    if use_ai:
        with st.spinner("Asking the local model (this can take a few seconds)..."):
            note, error = llm.explain(
                plan.summary_text(), context, base_url, model_name.strip() or None
            )
        if note:
            st.subheader("A note from your local model")
            st.write(note)
        else:
            st.caption(
                "The local model isn't reachable, so here is the plan without the "
                "AI note. Start the LM Studio server and try again."
            )
            with st.expander("Technical detail"):
                st.code(error)

    st.download_button(
        "Download reminders for your phone (.ics)",
        data=hy.build_ics(plan.events),
        file_name="hydrolocal-reminders.ics",
        mime="text/calendar",
        key=f"ics-{key}",
        help="Open the file on your phone or calendar app to get alarms. Works offline.",
    )


# ---------------------------------------------------------------- shift tab
with tab_shift:
    st.subheader("Plan my shift")
    c1, c2 = st.columns(2)
    start = c1.time_input("Shift starts", time(8, 0), key="s_start")
    end = c2.time_input("Shift ends", time(16, 30), key="s_end")
    b1, b2, b3 = st.columns(3)
    brk1 = b1.time_input("Break 1", time(10, 0), key="b1")
    brk2 = b2.time_input("Break 2 (lunch)", time(12, 30), key="b2")
    brk3 = b3.time_input("Break 3", time(14, 30), key="b3")
    d1, d2, d3 = st.columns(3)
    heat = d1.selectbox("How warm is your work area?", list(hy.HEAT_ML_PER_HOUR), index=1, key="s_heat")
    activity = d2.selectbox("How physical is the work?", list(hy.ACTIVITY_FACTOR), index=1, key="s_act")
    caffeine = d3.number_input("Coffee / energy drinks today", 0, 10, 2, key="s_caf")
    station = st.checkbox("I can keep water at my station", value=True, key="s_station")
    if st.button("Make my shift plan", type="primary", key="go_shift"):
        st.session_state["shift"] = (
            hy.shift_plan(at(start), at(end), [at(brk1), at(brk2), at(brk3)],
                          weight_kg, heat, activity, station),
            f"works a shift, {heat.lower()} work area, {activity.lower()} physical work, "
            f"{caffeine} caffeinated drinks today, water at station: {'yes' if station else 'no'}",
        )
    if "shift" in st.session_state:
        show(*st.session_state["shift"], key="shift")

# ---------------------------------------------------------------- everyday tab
with tab_daily:
    st.subheader("Gentle reminders through the day")
    e1, e2, e3 = st.columns(3)
    wake = e1.time_input("I wake up at", time(7, 0), key="e_wake")
    sleep = e2.time_input("I go to bed at", time(23, 0), key="e_sleep")
    every = e3.select_slider("Remind me every", options=[1.0, 1.5, 2.0, 3.0], value=2.0, key="e_every",
                             format_func=lambda x: f"{x:g} h")
    if st.button("Make my reminders", type="primary", key="go_daily"):
        st.session_state["daily"] = (
            hy.everyday_plan(datetime.now(), at(wake), at(sleep), weight_kg, every),
            "someone who often forgets to drink water and wants regular reminders",
        )
    if "daily" in st.session_state:
        show(*st.session_state["daily"], key="daily")

# ---------------------------------------------------------------- trek tab
with tab_trek:
    st.subheader("Pace your water on a trek")
    t1, t2, t3 = st.columns(3)
    t_start = t1.time_input("Trek starts", time(7, 0), key="t_start")
    t_hours = t2.number_input("Trek length (hours)", 0.5, 24.0, 5.0, 0.5, key="t_hours")
    t_water = t3.number_input("Water you carry (litres)", 0.5, 10.0, 2.0, 0.5, key="t_water")
    t_heat = st.selectbox("How warm is it?", list(hy.HEAT_ML_PER_HOUR), index=1, key="t_heat")
    if st.button("Make my trek plan", type="primary", key="go_trek"):
        st.session_state["trek"] = (
            hy.trek_plan(at(t_start), t_hours, int(t_water * 1000), weight_kg, t_heat),
            f"going on a {t_hours:g} hour trek carrying {t_water:g} L of water, {t_heat.lower()} weather",
        )
    if "trek" in st.session_state:
        show(*st.session_state["trek"], key="trek")

with st.expander("Where do these numbers come from?"):
    st.markdown(
        "- **Hot work:** the US CDC/NIOSH guidance of about 1 cup (8 oz) every 15-20 minutes, "
        "which is 24-32 oz (about 710-950 ml) per hour, and never more than 48 oz per hour. "
        "HydroLocal never suggests more than the top of that range.\n"
        "- **Comfortable conditions:** the US National Academies adequate intake for total "
        "water (about 2.7 L a day for women and 3.7 L for men, roughly 80% of it from drinks), "
        "spread over waking hours.\n"
        "- **Everything in between** (the 'warm' level, the body-weight scaling, the drinks "
        "before and after a shift, the trek reserve) is my own estimate, not from a source.\n\n"
        "These are general estimates, not medical advice. Details are in `hydration.py`."
    )

st.divider()
st.caption(
    "Open-weight model + local server + your data stays here. "
    "Numbers are rule-of-thumb estimates, not medical advice."
)
