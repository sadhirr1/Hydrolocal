# HydroLocal

A private hydration coach that runs entirely on your own computer. Built for a
friend who works on a production line, finds it hard to keep track of his water,
and gets dehydrated quickly.

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
- **Phone reminders** - every plan can be downloaded as an `.ics` calendar file;
  open it on your phone and the schedule becomes alarms that work offline.
- If the local model isn't running, the app still shows the schedule; only the
  written note is skipped.

## Run it on Windows

1. Install **Python** from python.org. On the first screen, tick **Add Python to PATH**.
2. Install **LM Studio** and download **google/gemma-4-e4b** (about 6 GB).
3. In LM Studio, open the **Developer** tab, load the model and click **Start Server**.
   Leave it running (it listens at `http://localhost:1234/v1`).
4. Open a terminal in this folder and run:

   ```
   py -m pip install -r requirements.txt
   py -m streamlit run app.py
   ```

   On Mac or Linux, use `python3` instead of `py`. If Windows says `py` isn't
   recognised, Python isn't installed yet (step 1): install it, then close and
   reopen the terminal.

5. Your browser opens the app at `http://localhost:8501`.

Run the tests (optional): `py -m pip install pytest` then `py -m pytest -q`.

Other models: the app asks LM Studio which model is loaded, so any chat model you
load there will work. HydroLocal was built and tested with `google/gemma-4-e4b`.

## Where the numbers come from

The amounts are estimates, and each constant in `hydration.py` is tagged with its source:

- **Hot work:** US CDC/NIOSH guidance for hot work: about 1 cup (8 oz) every 15-20
  minutes, which is 24-32 oz (about 710-950 ml) per hour, and never more than 48 oz
  per hour. HydroLocal never suggests more than the top of that range, and reminds
  you every 20 minutes when you say the work is hot.
- **Comfortable conditions:** the US National Academies adequate intake for total
  water: about 2.7 L a day for women and 3.7 L for men, roughly 80% of it from
  drinks. The "cool" level and the everyday daily target are based on this.
- **My own estimates (not from a source):** the "warm" level, scaling by body
  weight, the drinks before and after a shift, the largest single drink, and the trek
  reserve.

None of this is medical advice.

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

- The hydration numbers are **estimates**, not medical advice. Some are based on the
  sources above and some are my own, as listed.
- HydroLocal can't tell anyone why they feel unwell. Dizziness, fainting or
  confusion means stop, sit down, tell someone and get medical help.
- People with kidney, heart or other medical conditions should follow their
  doctor's advice about fluids.
- The local model only writes the explanation. It does not set the numbers and
  it is told not to diagnose, recommend brands, or suggest salt, supplements or food.

## Why open and local matters here

Shift times, body weight and health habits are personal. With an open-weight
model on the laptop, none of that is sent to a company server, it costs nothing
per message, it works with no internet, and the model can be swapped for another
one in LM Studio without changing the app.

## License

MIT - see `LICENSE`.
