# HydroLocal

A private hydration coach that runs entirely on your own computer. Built for a
friend who works on a production floor and is often dehydrated by the afternoon.

The schedule numbers are calculated by plain, readable Python (`hydration.py`).
An open-weight model, **Gemma**, running locally in **LM Studio**, writes the
friendly explanation. There is no cloud service, no account and no stored data.

## What it does

- **Shift at work** - enter shift times, breaks, how warm and physical the work
  is, and whether water can be kept at the station. You get a drinking schedule
  built around your breaks (night shifts that cross midnight work too).
- **Everyday reminders** - gentle reminders through the day for people who forget
  to drink.
- **Trek pacing** - spreads the water you carry across the whole trek, keeps a
  reserve, and warns you when you haven't packed enough.
- **Phone reminders** - every plan can be downloaded as an `.ics` calendar file
  that gives you alarms on any phone, offline.
- If the local model isn't running, the app still shows the schedule; only the
  written note is skipped.

## Run it on Windows

1. Install **Python** from python.org. On the first screen, tick **Add Python to PATH**.
2. Install **LM Studio** and download **google/gemma-4-e4b** (about 6 GB).
3. In LM Studio, open the **Developer** tab, load the model and click **Start Server**.
   Leave it running (it listens at `http://localhost:1234/v1`).
4. Open a terminal in this folder and run:

   ```
   pip install -r requirements.txt
   streamlit run app.py
   ```

5. Your browser opens the app. To prove it is local, turn Wi-Fi off and make a plan.

Run the tests (optional): `pip install pytest` then `python -m pytest -q`.

## Privacy note

Streamlit, the web library the interface uses, sends anonymous usage statistics by
default. HydroLocal ships a `.streamlit/config.toml` that turns this off and makes the
app reachable only from your own computer. Your plans and inputs are never sent anywhere.

## Files

| File | Purpose |
| --- | --- |
| `app.py` | The Streamlit web interface |
| `hydration.py` | Schedule calculations and `.ics` export (no AI, no network) |
| `llm.py` | Connects to the local model through LM Studio |
| `test_*.py` | Automated tests |

## Honest limits

- The hydration numbers are **rule-of-thumb estimates**, not medical advice. The
  constants at the top of `hydration.py` are meant to be reviewed and adjusted.
- HydroLocal can't tell anyone why they feel unwell. Dizziness, fainting or
  confusion means stop, sit down, tell someone and get medical help.
- People with kidney, heart or other medical conditions should follow their
  doctor's advice about fluids.
- The local model only writes the explanation. It does not set the numbers and
  it is told not to diagnose or recommend brands.

## Why open and local matters here

Shift times, body weight and health habits are personal. With an open-weight
model on the laptop, none of that is sent to a company server, it costs nothing
per message, it works with no internet, and the model can be swapped for another
one in LM Studio without changing the app.
