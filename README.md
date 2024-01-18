# AI Assistants

## Overview

The Assistants API enables you to create AI assistants in your own applications. These assistants are equipped with instructions and can utilize various models, tools, and knowledge to answer user questions. Currently, the API supports three types of tools: Code Interpreter, Retrieval, and Function calling. More tools will be added in the future.

## Benefits of using assistants

| Feature | Description |
|--------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Threads | Contains Messages and automatically handles the truncation of content to fit within the context of a model. |
| Files | Allows importing file content of different file formats. Can be used in tools such as Retrieval scenarios and analysis with Code Interpreter. |
| Tools | Includes Code Interpreter, Knowledge Retrieval, and Function calling.<br>  Code Interpreter allows executing code snippets.<br>  Knowledge Retrieval automatically chunks and embeds content in files for augmented retrieval scenarios.<br>  Function calling enables calling functions. |
| Tool composition | Enables using multiple tools in one Assistant. |

## Foundational concepts

| Term | Definition |
|--------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Assistant | An AI system specifically designed to utilize OpenAI's models and call tools. |
| Thread | A session of conversation between a user and an Assistant. Threads store Messages and automatically handle truncation to ensure that content fits within the context of the model. |
| Message | A piece of communication generated by either an Assistant or a user. Messages can contain text, images, and other files. Messages are stored as a list within a Thread. |
| Run | An instance of an Assistant being invoked on a Thread. The Assistant utilizes its configuration and the Messages within the Thread to perform tasks by calling models and tools. During a Run, the Assistant appends Messages to the Thread. |
| Run Step | A detailed record of the individual actions taken by the Assistant during a Run. These steps can include calling tools or generating Messages. Examining Run Steps provides insight into how the Assistant arrives at its final results. |

## Lifecycle

| Status | Description |
|--------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| queued | When Runs are initially created or when the required action is completed, they are placed in a queued status. They should quickly transition to an in_progress status. | | in_progress | While in_progress, the Assistant utilizes the model and tools to perform steps. The progress of the Run can be monitored by examining the Run Steps. |
| completed | The Run has successfully finished! You can now access all the Messages added by the Assistant to the Thread, as well as the steps taken by the Run. You can also continue the conversation by adding more user Messages to the Thread and initiating another Run. |
| requires_action | When using the Function calling tool, the Run will transition to a required_action state once the model determines the names and arguments of the functions to be called. You must then execute those functions and submit the outputs before the Run can proceed. If the outputs are not provided before the expires_at timestamp (approximately 10 minutes after creation), the Run will move to an expired status. |
| expired | This occurs when the function calling outputs were not submitted before the expires_at timestamp and the Run expires. Additionally, if the Run takes too long to execute and exceeds the time specified in expires_at, our systems will mark the Run as expired. |
| cancelling | You can attempt to cancel an in_progress Run by using the Cancel Run endpoint. Once the cancellation attempt is successful, the status of the Run will change to cancelled. However, cancellation is not guaranteed and may not always be possible. |
| cancelled | The Run was successfully cancelled. |
| failed | The reason for the failure can be viewed by examining the last_error object in the Run. The timestamp for the failure will be recorded under failed_at. |

### Reference Sample code

Reference:

- [OpenAI Assistant Sample](https://github.com/openai/openai-python/blob/main/examples/assistant.py)

```python
import time
from openai import AzureOpenAI

# gets API Key from environment variable OPENAI_API_KEY
client = AzureOpenAI(api_key=api_key,
        api_version=api_version,
        azure_endpoint=api_endpoint)

# Create an asssitant
assistant = client.beta.assistants.create(
    name="Math Tutor",
    instructions="You are a personal math tutor. Write and run code to answer math questions.",
    tools=[{"type": "code_interpreter"}],
    model="gpt-4-1106-preview",
)

# Create a thread
thread = client.beta.threads.create()

# Create a message
message = client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="I need to solve the equation `3x + 11 = 14`. Can you help me?",
)

# Create a run
run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id=assistant.id,
    instructions="Please address the user as Jane Doe. The user has a premium account.",
)

# Check the status of a run
print("checking assistant status. ")
while True:
    # Get the run information
    run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

    # If the run.status has changed to completed
    if run.status == "completed":
        print("done!")
        # Get the messages for a thread
        messages = client.beta.threads.messages.list(thread_id=thread.id)

        # Print the messages
        print("messages: ")
        for message in messages:
            assert message.content[0].type == "text"
            print({"role": message.role, "message": message.content[0].text.value})
        
        # Dispose of the assistant
        client.beta.assistants.delete(assistant.id)

        # Dispose of the thread
        client.beta.threads.delete(thread.id)

        break
    else:
        print("in progress...")
        time.sleep(5)
```

## Notebooks

| Topic | Description |
|----------------------|--------------------------------------------------|
| [Assistant-01: Foundational Concepts](notebooks/assistant-01-code_interpreter.ipynb) | Showcases the foundational concepts of Assistants such as threads, messages, runs, and tools. |
| [Assistant-04: Financial Summary bot](notebooks/assistant-04-function_la_email.ipynb) | Using Code Interpreter and Function calling this bot can summarize a financial news article, extract the ticker symbols from the article, get the latest stock prices and email a report. |
| [Assistant-06: Portpolio Reporting bot](notebooks/assistant-06-code_function_la_email.ipynb) | Code Interpreter and Function calling. |
| [Assistant-10: HR bot](notebooks/assistant-10-Travelbot.ipynb) | Using the Retrieval tool, provide files on different HR-related topics, and answer employees' questions about these topics. |
| [Assistant-11: Travel bot](notebooks/assistant-11-Travelbot.ipynb) | Using Code Interpreter, Function calling, and Retrieval, this bot can answer users' questions from a travel itinerary, split and calculate shared expenses, and block the outlook calendar. |
