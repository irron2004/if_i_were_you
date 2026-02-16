# Main Service Startup Failure Report

## Summary
- **Affected service:** `main-service`
- **Detected issue:** Application failed to start because the static assets directory referenced during startup was missing.
- **Resolution:** Create and track the missing `app/static` directory, provide a baseline stylesheet, and update the FastAPI application to resolve paths relative to the module so startup no longer depends on the working directory.

## Observed Symptoms
- Running `uvicorn app.main:app --reload --port 8000` exited immediately.
- The reloader traceback ended with:
  ```text
  RuntimeError: Directory 'app/static' does not exist
  ```
- Because the exception occurs during application import, the service never binds to the configured port, making health checks and the homepage unavailable.

## Root Cause Analysis
- `main-service/app/main.py` mounted a static directory using `StaticFiles(directory="app/static")`.
- The repository did not include an `app/static/` directory, so Starlette raised a runtime error while mounting static files during application startup.
- The relative path also relied on the process working directory. Launching the service from a different directory (e.g., repository root) would continue to fail even if the folder were later added.

## Resolution Steps
1. Added pathlib-based path resolution in `main.py` to compute the static and template directories relative to the module file.
2. Ensured the static directory exists at runtime with `mkdir(parents=True, exist_ok=True)` so the service can start even before assets are added.
3. Created `app/static/styles.css` as a starter stylesheet and linked it from the base template so static files are served successfully.

## Verification
- After applying the changes, starting the service with `uvicorn app.main:app --reload --port 8000` no longer raises the missing directory error.
- The homepage now loads successfully and serves the linked `/static/styles.css` asset.

## Recommendations
- Keep static assets under version control to avoid regressions.
- Consider adding an automated startup check (e.g., unit test) that imports the FastAPI application to catch missing directories during CI.
- Document the expected project layout in developer onboarding guides so future contributors create required folders alongside template changes.
