import requests
import os

from openai import OpenAI
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()
app = FastAPI()

# Define the request body schema using Pydantic
class MessageRequest(BaseModel):
    message: str
    assistant_id: str
    contact_id: int
    thread_id: Optional[str] = None

@app.post("/threads")
def threads(request: MessageRequest):
    """
    Accept a message, contact_id, and optional thread_id from the request body.
    Make an external API call, then return the response.
    """
    # Prepare the payload for the external API call
    payload = {
        "message": request.message,
        "contact_id": request.contact_id
    }

    client = OpenAI(
    api_key = os.environ.get("OPENAI_API_KEY"),  # This is the default and can be omitted
    )

    thread = client.beta.threads.create()
    
    message = client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=request.message
            )

    run = client.beta.threads.runs.create_and_poll(
                thread_id=thread.id,
                assistant_id=request.assistant_id,
                instructions="Please address the user as Jane Doe. The user has a premium account."
            )
    if run.status == 'completed': 
        messages = client.beta.threads.messages.list(
            thread_id=thread.id
        )
                # Extract text content from the latest message
        latest_message = messages.data[0]
          # First message is the latest
        message_content = latest_message.content[0].text.value
        return {
            "status": "success",
            "message": message_content
        }
        print(messages)
    else:
        print(run.status)
    # Include thread_id only if it’s provided
    if request.thread_id is not None:
        payload["thread_id"] = request.thread_id
