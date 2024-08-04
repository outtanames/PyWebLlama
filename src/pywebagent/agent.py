import base64
from enum import Enum
import json
import time
import logging
from pywebagent.env.browser import BrowserEnv
from langchain.schema import HumanMessage, SystemMessage
from langchain.chat_models import ChatOpenAI

import requests
import json
from groq import Groq
import os

import requests

logger = logging.getLogger(__name__)


TASK_STATUS = Enum("TASK_STATUS", "IN_PROGRESS SUCCESS FAILED")


class Task:
    def __init__(self, task, args) -> None:
        self.task = task
        self.args = args


def get_llm():
    return ChatOpenAI(
        model_name="gpt-4o",
        temperature=1,
        request_timeout=120,
        max_tokens=2000,
    )


def llama_70b(prompt: str, provider="baseten"):
  if provider == "baseten":
    s = requests.Session()
    with s.post(
        "https://model-jwd78r4w.api.baseten.co/production/predict",
        headers={"Authorization": "Api-Key vB3H7OSq.HCfqgTyxgyYKAp5palSauFwCV5UzAxSp"},
        data=json.dumps({
          "prompt": prompt,
          "stream": True,
          "max_tokens": 1024
        }),
        stream=False,
    ) as resp:
        resp.content
  elif provider == "groq":
    client = Groq(
        api_key=os.environ.get("GROQ_API_KEY"),
    )

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="llama-3.1-70b-versatile",
    )

    return chat_completion.choices[0].message.content
  else:
     raise ValueError("Invalid provider")
  

def llama_405b(prompt: str, provider="baseten"):
  if provider == "baseten":
    s = requests.Session()
    with s.post(
        "https://model-7wlxp82w.api.baseten.co/production/predict",
        headers={"Authorization": "Api-Key QLk2AhIS.ay5p1g5DPDeAcNqveNziEOmh2hW42b6Q"},
        data=json.dumps({
          "prompt": prompt,
          "stream": True,
          "max_tokens": 1024
        }),
        stream=False,
    ) as response:
        return str(response.content)
  elif provider == "groq":
    raise ValueError("Not implemented")
  else:
     raise ValueError("Invalid provider")
  

def generate_user_message(task, observation, num_history):
    # use last num_history actions
    if observation.env_state.log_history and num_history > 0:
        log_history = "\n".join(observation.env_state.log_history[-num_history:])
    else:
        log_history = ""

    marked_elements_tags = ", ".join(
        [
            f"({str(i)}) - <{elem['tag'].lower()}>"
            for i, elem in observation.marked_elements.items()
        ]
    )
    text_prompt = f"""
        Execution error: 
        {observation.error_message}

        URL: 
        {observation.url}

        Marked elements tags:
        {marked_elements_tags}
        
        Task: 
        {task.task}

        Log of last actions:
        {log_history}

        Task Arguments:
        {json.dumps(task.args, indent=4)}
        
    """
  

def generate_user_message_llama(task, page_summary_from_vision, url, num_history):
    if observation.env_state.log_history and num_history > 0:
        log_history = "\n".join(observation.env_state.log_history[-num_history:])
    else:
        log_history = ""

    text_prompt = f"""
        URL: 
        {url}
        Summary of page contents:
        {page_summary_from_vision}
        
        Task: 
        {task.task}
        Task Arguments:
        {json.dumps(task.args, indent=4)}
        
    """

    text_content = {"type": "text", "text": text_prompt}

    return HumanMessage(content=[text_content])


def generate_user_message_vision(task, observation):
    log_history = '\n'.join(observation.env_state.log_history if observation.env_state.log_history else [])
    marked_elements_tags = ', '.join([f"({str(i)}) - <{elem['tag'].lower()}>" for i, elem in observation.marked_elements.items()])
    text_prompt = f"""
        Execution error: 
        {observation.error_message}
        URL: 
        {observation.url}
        Summary of page contents:
        {marked_elements_tags}
        
        Task: 
        {task.task}
        Log of last actions:
        {log_history}
        Task Arguments:
        {json.dumps(task.args, indent=4)}
    """

    text_content = {"type": "text", "text": text_prompt}

    return HumanMessage(content=[text_content])


def generate_system_message_llama():
    system_prompt = """
    You are an AI agent that controls a webpage using python code, in order to achieve a task.
    You are provided a bulleted list of page elements from a
    vision model, and you decide on the next python line to execute.
    You can use the following functions:
    - actions.click(element_id, log_message) # click on an element
    - actions.input_text(element_id, text, clear_before_input, log_message) # Use clear_before_input=True to replace the text instead of appending to it. Never use this method on a combobox.
    - actions.upload_files(element_id, files: list, log_message) # use this instead of click if clicking is expected to open a file picker
    - actions.scroll(direction, log_message) # scroll the page up or down. direction is either 'up' or 'down'.
    - actions.combobox_select(element_id, option, log_message) # select an option from a combobox.
    - actions.finish(did_succeed, output: dict, reason) # the task is complete with did_succeed=True or False, and a text reason. output is optional dictionary of output values if the task succeeded.
    - actions.act(url: str, task: str, log_message, **kwargs) # run another agent on a different webpage. The sub-agent will run until it finishes and will output a result which you can use later. Useful for getting auth details from email for example.
                                                              # task argument should be described in natural language. kwargs are additional arguments the sub-agent needs to complete the task. YOU MUST PROVIDE ALL NEEDED ARGUMENTS, OTHERWISE THE SUB-AGENT WILL FAIL.
    the element_id is always an integer and will be provided in the summary with each possible page item. 
    log_message is a short one sentence explanation of what the action does.
    Do not use keyword arguments, all arguments are positional.
    
    IMPORTANT: ONLY ONE WEBPAGE FUNCTION CALL IS ALLOWED, EXCEPT FOR FORMS WHERE MULTIPLE CALLS ARE ALLOWED TO FILL MULTIPLE FIELDS! NOTHING IS ALLOWED AFTER THE "```" ENDING THE CODE BLOCK
    Response format:
    Reasoning:
    Explanation for the next action, particularly focusing on interpreting the attached screenshot image.
    Code:
    ```python
    # variable definitions and non-webpage function calls are allowed
    ...
    # a single webpage function call. 
    actions.func_name(args..)
    ```
    """
    return SystemMessage(content=system_prompt)


def generate_system_message_vision():
    system_prompt = """
    You are an AI agent that summarizes an annotated webpage to generate a list of actions that can be taken and their 
    associated visual elements, in order to achieve a task.
    You are provided a screenshot of the webpage at each timeframe, and you return a bulleted list of page elements with
    the associated element id as well a description of what the element does. The element might be:
    * a clickable button
    * a text field
    * a file upload
    * a scroll bar
    etc. You should return these elements in the order they appear in the screenshot.
    """
    return SystemMessage(content=system_prompt)

def generate_page_summary(task, observation):
    logger.info("Generating page summary...")
    vision_chat = get_llm()

    system_message = generate_system_message_vision()
    user_message = generate_user_message(task, observation, num_history=0)

    try:
        page_summary = vision_chat([system_message, user_message])
    except:
        # This sometimes solves the RPM limit issue
        logger.warning("Failed to get response from OpenAI, trying again in 30 seconds")
        time.sleep(30)
        page_summary = vision_chat([system_message, user_message])

    return page_summary.content 


def calculate_action_llama(task, observation):
    system_message = generate_system_message_llama()

    page_summary = generate_page_summary(task, observation)

    # Going to generate from both gpt and llama for now
    user_message = generate_user_message_llama(task, page_summary, observation.url, num_history=3)

    # join the system and user messages for now
    nav_prompt_content = "This is the system prompt: " + \
                            system_message.content + "\n" + \
                            "This is the user prompt: " + \
                            user_message.content[0]['text'] 
    navigation_prompt = SystemMessage(nav_prompt_content)

    try:
        nav_response = llama_70b(navigation_prompt.content, provider="groq")
    except Exception as e:
        # This sometimes solves the RPM limit issue
        logger.warning("Failed to get response from llama client: " + str(e))
        time.sleep(10)
        nav_response = llama_70b(navigation_prompt.content, provider="groq")

    code_to_execute = extract_code(nav_response)

    return code_to_execute

    screenshot_binary = observation.screenshot
    base64_image = base64.b64encode(screenshot_binary).decode("utf-8")
    image_content = {
        "type": "image_url",
        "image_url": {
            "url": f"data:image/jpeg;base64,{base64_image}",
            "detail": "high",  # low, high or auto
        },
    }
    text_content = {"type": "text", "text": text_prompt}

    return HumanMessage(content=[text_content, image_content])


def generate_system_message():
    system_prompt = """
    You are an AI agent that controls a webpage using python code, in order to achieve a task.
    You are provided a screenshot of the webpage at each timeframe, and you decide on the next python line to execute.
    You can use the following functions:
    - actions.click(element_id, log_message) # click on an element
    - actions.input_text(element_id, text, clear_before_input, log_message) # Use clear_before_input=True to replace the text instead of appending to it. Never use this method on a combobox.
    - actions.upload_files(element_id, files: list, log_message) # use this instead of click if clicking is expected to open a file picker
    - actions.scroll(direction, log_message) # scroll the page up or down. direction is either 'up' or 'down'.
    - actions.combobox_select(element_id, option, log_message) # select an option from a combobox.
    - actions.finish(did_succeed, output: dict, reason) # the task is complete with did_succeed=True or False, and a text reason. output is optional dictionary of output values if the task succeeded.
    - actions.act(url: str, task: str, log_message, **kwargs) # run another agent on a different webpage. The sub-agent will run until it finishes and will output a result which you can use later. Useful for getting auth details from email for example.
                                                              # task argument should be described in natural language. kwargs are additional arguments the sub-agent needs to complete the task. YOU MUST PROVIDE ALL NEEDED ARGUMENTS, OTHERWISE THE SUB-AGENT WILL FAIL.
    element_id is always an integer, and is visible as a green label with white number around the TOP-LEFT CORNER OF EACH ELEMENT. Make sure to examine all green highlighted elements before choosing one to interact with.
    log_message is a short one sentence explanation of what the action does.
    Do not use keyword arguments, all arguments are positional.

    
    IMPORTANT: ONLY ONE WEBPAGE FUNCTION CALL IS ALLOWED, EXCEPT FOR FORMS WHERE MULTIPLE CALLS ARE ALLOWED TO FILL MULTIPLE FIELDS! NOTHING IS ALLOWED AFTER THE "```" ENDING THE CODE BLOCK
    IMPORTANT: LOOK FOR CUES IN THE SCREENSHOTS TO SEE WHAT PARTS OF THE TASK ARE COMPLETED AND WHAT PARTS ARE NOT. FOR EXAMPLE, IF YOU ARE ASKED TO BUY A PRODUCT, LOOK FOR CUES THAT THE PRODUCT IS IN THE CART.
    Response format:

    Reasoning:
    Explanation for the next action, particularly focusing on interpreting the attached screenshot image.

    Code:
    ```python
    # variable definitions and non-webpage function calls are allowed
    ...
    # a single webpage function call. 
    actions.func_name(args..)
    ```
    """
    return SystemMessage(content=system_prompt)




def extract_code(text):
    """
    Extracts all text in a string following the pattern "'\nCode:\n".
    """
    pattern = "\nCode:\n```python\n"
    start_index = text.find(pattern)
    if start_index == -1:
        raise Exception("Code not found")

    # Extract the text following the pattern, without the trailing "```"
    extracted_text = text[start_index + len(pattern) : -3]

    return extracted_text


def calculate_next_action(task, observation, num_history):
    llm = get_llm()

    system_message = generate_system_message()
    user_message = generate_user_message(task, observation, num_history)

    try:
        ai_message = llm([system_message, user_message])
    except:
        # This sometimes solves the RPM limit issue
        logger.warning("Failed to get response from OpenAI, trying again in 30 seconds")
        time.sleep(30)
        ai_message = llm([system_message, user_message])

    logger.info(f"AI message: {ai_message.content}")

    code_to_execute = extract_code(ai_message.content)

    return code_to_execute


def get_task_status(observation):
    if observation.env_state.has_successfully_completed:
        return TASK_STATUS.SUCCESS
    elif observation.env_state.has_failed:
        return TASK_STATUS.FAILED
    else:
        return TASK_STATUS.IN_PROGRESS


def act(url, task, num_history, max_actions=40, **kwargs):
    task = Task(task=task, args=kwargs)

    browser = BrowserEnv(headless=False)
    observation = browser.reset(url)

    for i in range(max_actions):
        # action = calculate_next_action(task, observation, num_history)
        action = calculate_action_llama(task, observation) 
        observation = browser.step(action, observation.marked_elements)
        task_status = get_task_status(observation)
        if task_status in [TASK_STATUS.SUCCESS, TASK_STATUS.FAILED]:
            return task_status, observation.env_state.output

    logger.warning(f"Reached {i} actions without completing the task.")
    return TASK_STATUS.FAILED, observation.env_state.output
