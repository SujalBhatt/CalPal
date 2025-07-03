# CalPal

**CalPal** is an AI calendar assistant that helps you book appointments and chat about your schedule. It features a modern, animated frontend (Streamlit) and a FastAPI backend that integrates with Google Calendar and Google Gemini (Generative AI) for natural language understanding and event management.

---

## Features

- **Conversational Booking**: Chat with CalPal to book, view, or discuss appointments in natural language.
- **Google Calendar Integration**: Automatically creates and manages events using your Google Calendar.
- **AI-Powered Understanding**: Uses Google Gemini to extract event details from free-form text.
- **API Key Rotation**: Supports multiple Gemini API keys for robust, quota-resistant operation.

---

## Project Structure

```
CalPal/
  backend/
    agent.py                # AI logic, Gemini integration, booking info extraction
    calendar_utils.py       # Google Calendar API utilities (event creation, free slot finding)
    list_gemini_models.py   # Script to list available Gemini models
    main.py                 # FastAPI app (chat and booking endpoints)
    requirements.txt        # Backend dependencies
    venv/                   # (optional) Python virtual environment
  frontend/
    app.py                  # Streamlit app (UI, chat, starfield, input, avatars)
    requirements.txt        # Frontend dependencies
  requirements.txt          # (optional) Combined dependencies
  service_account.json      # Google service account credentials
```

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd CalPal
```

### 2. Set Up Python Virtual Environment

```bash
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Windows CMD:
.venv\Scripts\activate.bat
# On Mac/Linux:
source .venv/bin/activate
```

### 3. Install Dependencies

Install both backend and frontend dependencies (from the project root):

```bash
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt
```

Or, if you have a combined `requirements.txt` in the root:

```bash
pip install -r requirements.txt
```

### 4. Set Up Google API Credentials

- Create a Google Cloud project and enable the Calendar API.
- Download your `service_account.json` and place it in the project root.
- Set your calendar ID as an environment variable or in `.env` (see below).

### 5. Configure Environment Variables

Create a `.env` file in the backend directory with:

```
GEMINI_API_KEYS=your_gemini_api_key1,your_gemini_api_key2
GOOGLE_CALENDAR_ID=your_calendar_id
```

- You can use multiple Gemini API keys, separated by commas.

---

## Running the App

### 1. Start the Backend (FastAPI)

```bash
cd backend
uvicorn main:app --reload
```

The backend will be available at `http://localhost:8000`.

### 2. Start the Frontend (Streamlit)

In a new terminal (with the venv activated):

```bash
cd frontend
streamlit run app.py
```

The frontend will open in your browser (usually at `http://localhost:8501`).

---

## Usage

- **Chat**: Type your message in the input box and press the rocket button 🚀.
- **Book Events**: Ask CalPal to book meetings, appointments, or events in natural language (e.g., "Book a meeting with John tomorrow at 2pm").
- **View Responses**: CalPal will reply in a modern chat interface, and events will be added to your Google Calendar.

---

## Backend API

- `POST /chat` — Accepts `{ "message": "..." }`, returns `{ "response": "..." }`
- `POST /book` — Accepts event details, creates a calendar event

---

## Dependencies

### Backend

- fastapi
- uvicorn
- google-api-python-client
- google-auth
- google-auth-httplib2
- google-auth-oauthlib
- langchain
- google-generativeai
- python-dotenv

### Frontend

- streamlit
- requests

---

## Customization

- **Space Theme**: All UI elements are styled for a cosmic look (see `frontend/app.py`).
- **Google Calendar**: Change the calendar ID in your `.env` or environment variables.
- **Gemini Model**: The backend uses Gemini 1.5 Flash by default; see `agent.py` for customization.

---

## License

MIT License

---

## Acknowledgments

- [Streamlit](https://streamlit.io/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Google Gemini](https://ai.google.dev/)
- [Google Calendar API](https://developers.google.com/calendar)
``` 