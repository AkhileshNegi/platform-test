import requests
import os

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
    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
    )

    try:
        if request.thread_id:
            # Check for any active runs on the thread
            try:
                runs = client.beta.threads.runs.list(thread_id=request.thread_id)
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
                            "thread_id": request.thread_id,
                        }
            except openai.NotFoundError as e:
                # Handle invalid thread ID
                return {
                    "status": "error",
                    "message": "Invalid thread ID provided",
                    "thread_id": request.thread_id,
                }

            # Use existing thread
            message = client.beta.threads.messages.create(
                thread_id=request.thread_id, role="user", content=request.message
            )
        else:
            # Create new thread
            thread = client.beta.threads.create()
            message = client.beta.threads.messages.create(
                thread_id=thread.id, role="user", content=request.message
            )
            request.thread_id = thread.id

        # Run the assistant
        run = client.beta.threads.runs.create_and_poll(
            thread_id=request.thread_id,
            assistant_id=request.assistant_id,
            instructions="Please address the user as Jane Doe. The user has a premium account.",
        )

        if run.status == "completed":
            messages = client.beta.threads.messages.list(thread_id=request.thread_id)
            # Extract text content from the latest message
            latest_message = messages.data[0]  # First message is the latest
            message_content = latest_message.content[0].text.value
            return {
                "status": "success",
                "message": message_content,
                "thread_id": request.thread_id,
            }
        else:
            return {
                "status": "error",
                "message": f"Run failed with status: {run.status}",
                "thread_id": request.thread_id,
            }
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