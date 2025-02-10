import os
import requests
from openai import OpenAI
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
import openai


# Load variables from .env
load_dotenv()
app = FastAPI()


# Define the request body schema using Pydantic
class MessageRequest(BaseModel):
    question: str
    assistant_id: str
    callback_url: str
    thread_id: Optional[str] = None
    # Allow additional fields

    class Config:
        extra = "allow"


async def send_callback(callback_url: str, data: dict):
    """Send results to the callback URL"""
    try:

        # Create a session with SSL verification disabled
        session = requests.Session()
        session.verify = False
        # Use the session to make the request
        response = session.post(callback_url, json=data)

        response.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"Callback failed: {str(e)}")
        return False


@app.post("/threads")
async def threads(request: MessageRequest):
    """
    Accept a question, assistant_id, callback_url, and optional thread_id from the request body.
    Make an external API call, then return the response.
    """
    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
    )

    try:
        if request.thread_id:
            # Check for any active runs on the thread
            try:
                runs = client.beta.threads.runs.list(
                    thread_id=request.thread_id)
                # Get the most recent run (first in the list)
                if runs.data and len(runs.data) > 0:
                    latest_run = runs.data[0]
                    if latest_run.status in [
                        "queued",
                        "in_progress",
                        "requires_action",
                    ]:
                        return {
                            "status": "error",
                            "message": f"There is an active run on this thread (status: {latest_run.status}). Please wait for it to complete.",
                        }
            except openai.NotFoundError as _e:
                # Handle invalid thread ID
                return {
                    "status": "error",
                    "message": f"Invalid thread ID provided {request.thread_id}",
                }

            # Use existing thread
            message = client.beta.threads.messages.create(
                thread_id=request.thread_id, role="user", content=request.question
            )
        else:
            # Create new thread
            thread = client.beta.threads.create()
            message = client.beta.threads.messages.create(
                thread_id=thread.id, role="user", content=request.question
            )
            request.thread_id = thread.id

        # Send immediate response
        initial_response = {
            "status": "processing",
            "message": "Run started",
            "thread_id": request.thread_id,
        }

        # Start the run
        run = client.beta.threads.runs.create_and_poll(
            thread_id=request.thread_id,
            assistant_id=request.assistant_id,
        )

        if run.status == "completed":
            messages = client.beta.threads.messages.list(
                thread_id=request.thread_id)
            latest_message = messages.data[0]
            message_content = latest_message.content[0].text.value
            callback_response = {
                "status": "success",
                "message": message_content,
                "thread_id": request.thread_id,
                # Include additional fields
                **request.model_dump(exclude={'question', 'assistant_id', 'callback_url', 'thread_id'})
            }
        else:
            callback_response = {
                "status": "error",
                "message": f"Run failed with status: {run.status}",
                "thread_id": request.thread_id,
                # Include additional fields
                **request.model_dump(exclude={'question', 'assistant_id', 'callback_url', 'thread_id'})
            }

        # Send callback with results
        await send_callback(request.callback_url, callback_response)

        return initial_response

    except openai.OpenAIError as e:
        # Handle any other OpenAI API errors
        error_str = str(e)
        if "'message': " in error_str:
            # Extract text between 'message': " and the next "
            start = error_str.find("'message': ") + len("'message': \"")
            end = error_str.find("\"", start)
            error_message = error_str[start:end]
        else:
            error_message = error_str
        return {"status": "error", "message": error_message}
