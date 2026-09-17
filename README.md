# Headroom Streamlit Playground

A small Streamlit application for testing Headroom's local context compression.

Paste JSON, logs, code, or another large tool output to compare token counts and
inspect the compressed result. The deployment disables Headroom's large ML prose
model so it remains practical on Streamlit Community Cloud.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

No API key is required. Headroom's anonymous beacon is disabled by the app.

