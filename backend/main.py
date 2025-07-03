from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent import chat_with_agent
from calendar_utils import create_event
import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

class BookingRequest(BaseModel):
    summary: str
    start_time: str  # ISO format
    end_time: str    # ISO format
    description: str = None

@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    response = chat_with_agent(req.message)
    return {"response": response}

@app.post("/book")
def book_endpoint(req: BookingRequest):
    start = datetime.datetime.fromisoformat(req.start_time)
    end = datetime.datetime.fromisoformat(req.end_time)
    event = create_event(req.summary, start, end, req.description)
    return {"event": event} 