import shelve
import time
import os

from typing import List
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

api_URI = os.getenv("OPENAI_URI")
api_KEY = os.getenv("OPENAI_KEY")
api_version = os.getenv("OPENAI_VERSION")
gpt_deployment_name = os.getenv("OPENAI_GPT_DEPLOYMENT")
ada_deployment_name = os.getenv("OPENAI_ADA_DEPLOYMENT")


def get_openai_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=api_KEY,
        api_version=api_version,
        azure_endpoint=api_URI)


def create_assistant(client: AzureOpenAI, name: str, instructions: str, tools, model: str):
    assistant = client.beta.assistants.create(
        name=name,
        instructions=instructions,
        tools=tools,
        model=model,
    )
    return assistant


def check_if_assistant_exists(assistant_id):
    with shelve.open("assistant_db") as assistant_shelf:
        return assistant_shelf.get(assistant_id, None)


def store_assistant(assistant_id):
    with shelve.open("assistant_db", writeback=True) as assistant_shelf:
        assistant_shelf[assistant_id] = assistant_id


def check_if_thread_exists(wa_id):
    with shelve.open("threads_db") as threads_shelf:
        return threads_shelf.get(wa_id, None)


def store_thread(wa_id, thread_id):
    with shelve.open("threads_db", writeback=True) as threads_shelf:
        threads_shelf[wa_id] = thread_id


def __run_assistant(client, assistant, thread):
    # Run the assistant
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
    )

    # Wait for completion
    while run.status != "completed":
        # Be nice to the API
        time.sleep(0.5)
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id, run_id=run.id)

    # Retrieve the Messages
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    new_message = messages.data[0].content[0].text.value
    print(f"Generated message: {new_message}")
    return new_message


def generate_response(client, assistant, message_body, wa_id, name):

    # Check if there is already a thread_id for the wa_id
    thread_id = check_if_thread_exists(wa_id)

    # If a thread doesn't exist, create one and store it
    if thread_id is None:
        print(f"Creating new thread for {name} with wa_id {wa_id}")
        thread = client.beta.threads.create()
        store_thread(wa_id, thread.id)
        thread_id = thread.id

    # Otherwise, retrieve the existing thread
    else:
        print(f"Retrieving existing thread for {name} with wa_id {wa_id}")
        thread = client.beta.threads.retrieve(thread_id)

    # Add message to thread
    message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message_body,
    )

    # Run the assistant and get the new message
    new_message = __run_assistant(client, assistant, thread)
    print(f"To {name}:", new_message)
    return new_message
