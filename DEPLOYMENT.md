# Deployment Guide

## Recommended first deployment: Streamlit Community Cloud

This app is already structured for hosted use:

- Customers only access the web app URL.
- API keys stay in platform secrets.
- Uploaded videos and generated analysis files are stored in per-request temporary folders.
- The UI hides API settings when server-side secrets are configured.

## 1. Prepare the repository

Commit these source files to GitHub:

- `app.py`
- `analyze_release.py`
- `coach_ai_new.py`
- `requirements.txt`
- `.streamlit/secrets.toml.example`

Do not commit:

- `.streamlit/secrets.toml`
- `.env`
- `venv/`
- uploaded videos
- generated screenshots/results

The included `.gitignore` already excludes those files.

## 2. Configure Streamlit secrets

In Streamlit Community Cloud, open the app's advanced settings and paste:

```toml
AI_COACH_PROVIDER = "openai"
OPENAI_API_KEY = "your-openai-api-key"
AI_COACH_MODEL = "gpt-4.1-mini"
SHOW_API_SETTINGS = "false"
```

For Gemini instead:

```toml
AI_COACH_PROVIDER = "gemini"
GEMINI_API_KEY = "your-gemini-api-key"
AI_COACH_MODEL = "gemini-2.5-flash-lite"
SHOW_API_SETTINGS = "false"
```

## 3. Deploy

Create a Streamlit Community Cloud app from the GitHub repository and set:

- Main file path: `app.py`
- Python dependencies: loaded from `requirements.txt`
- Secrets: pasted from the examples above

## 4. Cost notes

Streamlit Community Cloud is a good free starting point for demos and early customer testing.
AI model calls still bill to the API account whose key is stored in secrets.

For production with login, customer quotas, payments, or stricter privacy controls, migrate to a managed server platform such as Google Cloud Run and store secrets in the platform secret manager.
