import shelve
import time
import os

from typing import List
from openai import AsyncAzureOpenAI, AzureOpenAI
from dotenv import load_dotenv

# Global variables

# List of assistants created
ai_assistants = []
# List of threads created
ai_threads = []


load_dotenv()

api_URI = os.getenv("OPENAI_URI")
api_KEY = os.getenv("OPENAI_KEY")
api_version = os.getenv("OPENAI_VERSION")
gpt_deployment_name = os.getenv("OPENAI_GPT_DEPLOYMENT")
ada_deployment_name = os.getenv("OPENAI_ADA_DEPLOYMENT")
email_URI = os.getenv("EMAIL_URI")


def clear_shelves():
    with shelve.open("assistant_db") as assistant_shelf:
        assistant_shelf.clear()
    with shelve.open("threads_db") as threads_shelf:
        threads_shelf.clear()


def get_async_openai_client() -> AsyncAzureOpenAI:
    return AsyncAzureOpenAI(
        api_key=api_KEY,
        api_version=api_version,
        azure_endpoint=api_URI)


def get_openai_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=api_KEY,
        api_version=api_version,
        azure_endpoint=api_URI)


def create_assistant(client, **kwargs):
    assistant = client.beta.assistants.create(**kwargs)
    __add_assistant(assistant)
    return assistant


def check_if_assistant_exists(assistant_id):
    with shelve.open("assistant_db") as assistant_shelf:
        return assistant_shelf.get(assistant_id, None)


def store_assistant(assistant_id):
    with shelve.open("assistant_db", writeback=True) as assistant_shelf:
        assistant_shelf[assistant_id] = assistant_id


def check_if_thread_exists(user_id):
    with shelve.open("threads_db") as threads_shelf:
        return threads_shelf.get(user_id, None)


def store_thread(user_id, thread):
    with shelve.open("threads_db", writeback=True) as threads_shelf:
        __add_thread(thread)
        threads_shelf[user_id] = thread.id


def __run_assistant(client, assistant, thread):
    # Run the assistant
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
    )

    # Wait for completion
    # not (run.status == "completed" or run.status or "failed" or run.status or "requires_action" or run.status or "expired" or run.status and "cancelled"):
    # or run.status != "failed" or run.status != "requires_action" or run.status != "expired" or run.status != "cancelled":
    while not (run.status == "completed" or run.status == "expired" or run.status == "cancelled" or run.status == "requires_action" or run.status == "failed"):
        # Be nice to the API
        time.sleep(0.5)
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id, run_id=run.id)

    if run.status == "failed" or run.status == "cancelled":
        print("Run failed or cancelled")
        return None

    if run.status == "expired":
        print("Run expired")
        return None

    if run.status == "requires_action":
        print("This a function assistant that requires action")
        return None

    # Retrieve the Messages
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    new_message = messages.data[0].content[0].text.value
    print(f"Generated message: {new_message}")
    return new_message


def generate_response(client, assistant, message_body, user_id, name):

    # Check if there is already a thread_id for the user_id
    thread_id = check_if_thread_exists(user_id)

    # If a thread doesn't exist, create one and store it
    if thread_id is None:
        print(f"Creating new thread for {name} with user_id {user_id}")
        thread = client.beta.threads.create()
        store_thread(user_id, thread)
        thread_id = thread.id
    # Otherwise, retrieve the existing thread
    else:
        print(f"Retrieving existing thread for {name} with user_id {user_id}")
        thread = client.beta.threads.retrieve(thread_id)
        __add_thread(thread)

    # Add message to thread
    message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message_body,
    )

    # Run the assistant and get the new message
    new_message = __run_assistant(client, assistant, thread)
    if new_message is None:
        print("Run failed, cancelling thread")
        return None

    print(f"To {name}:", new_message)
    return new_message


def __add_assistant(assistant):
    for item in ai_assistants:
        if item.id == assistant.id:
            return
    ai_assistants.append(assistant)
    print("Added assistant: ", assistant.id, len(ai_assistants))


def __add_thread(thread):
    for item in ai_threads:
        if item.id == thread.id:
            return
    ai_threads.append(thread)
    print("Added thread: ", thread.id, len(ai_threads))


def cleanup(client):
    print("Deleting: ", len(ai_assistants), " assistants.")
    for assistant in ai_assistants:
        print(client.beta.assistants.delete(assistant.id))
    print("Deleting: ", len(ai_threads), " threads.")
    for thread in ai_threads:
        print(client.beta.threads.delete(thread.id))
