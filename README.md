# FastAPI Basic Setup

This repository contains a basic setup for a FastAPI application in Python. It provides a minimal example of how to create a single endpoint (`/threads`) and run a FastAPI server.

## Features

- **FastAPI**: A modern, fast (high-performance) web framework for building APIs with Python.
- **/threads endpoint**: A simple endpoint to get you started with OpenAI threads. Pass a thread_id to continue an existing conversation, or leave it out to start fresh.

## Getting Started

1. Create `.env` file

```bash
cp .env .env.example
```

2. Add OpenAI API key in `.env` file

3. Source `.env` file

```bash
source .env
```

4. Start Server

```bash
fastapi dev main.py
```

## Use Endpoint

```bash

curl -X 'POST' \
  'http://127.0.0.1:8000/threads' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "message": "Tell me about Glific",
  "assistant_id": "asst_fz7oIxxxxx",
"thread_id": "thread_UHzQGCsxxxxNL",
  "contact_id": 10
}'

```
