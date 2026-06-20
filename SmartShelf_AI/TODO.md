# SmartShelf_AI - Fix & Update TODO

## Plan Summary
- Remove hard-coded secrets (Gemini API key + Postgres password) and replace with environment variables.
- Make Gemini Vision JSON parsing robust.
- Wire real vision extraction into the Streamlit app (replace mock detected assets).
- Remove suspicious placeholder comment in `database_backend.py`.

## Steps
- [x] Step 1: Update `ai_chef.py` to use `GOOGLE_API_KEY` env var and safer JSON parsing.
- [x] Step 5: Run a quick syntax check (`python -m py_compile`) on modified files.

- [x] Step 2: Update `database_backend.py` to use `DATABASE_PASSWORD` env var.
- [x] Step 3: Update `app.py` to call `analyze_shelf_image(uploaded_image)` and insert returned items.
- [x] Step 4: Remove placeholder comment in `database_backend.py`.
- [ ] Step 5: Run a quick syntax check (`python -m py_compile`) on modified files.


