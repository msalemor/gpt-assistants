import shelve
import time
import os
import datetime
import pytz
import requests

from openai import AsyncAzureOpenAI, AzureOpenAI
from dotenv import load_dotenv

# Global variables

# List of assistants created
ai_assistants = []
# List of threads created
ai_threads = []
# List of files uploaded
ai_files = []


load_dotenv()

api_URI = os.getenv("OPENAI_URI")
api_KEY = os.getenv("OPENAI_KEY")
api_version = os.getenv("OPENAI_VERSION")
gpt_deployment_name = os.getenv("OPENAI_GPT_DEPLOYMENT")
ada_deployment_name = os.getenv("OPENAI_ADA_DEPLOYMENT")
email_URI = os.getenv("EMAIL_URI")
event_URI = os.getenv("CALENDAR_EMAIL_URI")


def clear_shelves():
    with shelve.open("assistant_db") as assistant_shelf:
        assistant_shelf.clear()
    with shelve.open("threads_db") as threads_shelf:
        threads_shelf.clear()


# TODO: Consider removing this
def get_async_openai_client(**kwargs) -> AsyncAzureOpenAI:
    return AsyncAzureOpenAI(**kwargs)

# TODO: Consider removing this


def get_openai_client(**kwargs) -> AzureOpenAI:
    return AzureOpenAI(**kwargs)


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


def __run_assistant(client, assistant, thread, function_calling_fuc=None):
    # Run the assistant
    # TODO: Add instructions to the thread
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
    )

    # Wait for completion
    # not (run.status == "completed" or run.status or "failed" or run.status or "requires_action" or run.status or "expired" or run.status and "cancelled"):
    # or run.status != "failed" or run.status != "requires_action" or run.status != "expired" or run.status != "cancelled":
    while not (run.status == "completed" or run.status == "expired" or run.status == "cancelled" or run.status == "failed"):
        # Be nice to the API
        time.sleep(2)
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id, run_id=run.id)

        if run.status == "requires_action":
            if function_calling_fuc is not None:
                function_calling_fuc(client, thread, run)
            else:
                print("This a function assistant that requires action")
                return None

    if run.status == "failed" or run.status == "cancelled":
        print("Run failed or cancelled")
        return None

    if run.status == "expired":
        print("Run expired")
        return None

    # Retrieve the Messages
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    new_message = messages.data[0].content[0].text.value
    print(f"Generated message: {new_message}")
    return new_message


def generate_response(client, assistant, message_body, user_id, name, function_calling_fuc=None):

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
        content=f"Today is: {get_formatted_datetime()}\n\n{message_body}",
    )

    # Run the assistant and get the new message
    new_message = __run_assistant(
        client, assistant, thread, function_calling_fuc)
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


def __add_file(file):
    for item in ai_files:
        if item.id == file.id:
            return
    ai_files.append(file)
    print("Added file: ", file.id, len(ai_files))


def upload_file(client, path):
    # Upload a file with an "assistants" purpose
    file = client.files.create(file=open(path, "rb"), purpose="assistants")
    __add_file(file)
    return file


def get_counts():
    return len(ai_assistants), len(ai_threads), len(ai_files)


def cleanup(client):
    print("Deleting: ", len(ai_assistants), " assistants.")
    for assistant in ai_assistants:
        print(client.beta.assistants.delete(assistant.id))
    print("Deleting: ", len(ai_threads), " threads.")
    for thread in ai_threads:
        print(client.beta.threads.delete(thread.id))
    print("Deleting: ", len(ai_files), " files.")
    for file in ai_files:
        print(client.files.delete(file.id))


def get_localized_datetime(timezone='America/New_York'):
    now = datetime.datetime.now(pytz.timezone(timezone))
    return now.isoformat()


def get_formatted_datetime():
    return datetime.datetime.now().strftime("%x %X")


def send_email(json_payload):
    headers = {'Content-Type': 'application/json'}
    response = requests.post(email_URI, json=json_payload, headers=headers)
    if response.status_code == 202:
        print("Email sent to: " + json_payload['to'])


def send_event(json_payload):
    headers = {'Content-Type': 'application/json'}
    response = requests.post(event_URI, json=json_payload, headers=headers)
    if response.status_code == 202:
        print("Event processed")
