import base64
import re
from enum import Enum
import os
import json
import time
import logging
from pywebagent.env.browser import BrowserEnv
from openai import OpenAI

from langchain.schema import HumanMessage, SystemMessage
from langchain.chat_models import ChatOpenAI

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


def generate_user_message(task, observation):
    log_history = "\n".join(
        observation.env_state.log_history if observation.env_state.log_history else []
    )
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

    # return HumanMessage(content=[text_content, image_content])
    return text_content, image_content


def generate_system_message():
    # IMPORTANT: ONLY ONE WEBPAGE FUNCTION CALL IS ALLOWED, EXCEPT FOR FORMS WHERE MULTIPLE CALLS ARE ALLOWED TO FILL MULTIPLE FIELDS! NOTHING IS ALLOWED AFTER THE "```" ENDING THE CODE BLOCK
    system_prompt = """
    You are an AI agent that controls a webpage using python code, in order to achieve a task.
    You are provided a screenshot of the webpage at each timeframe, and you decide on the next python line to execute.

    Please provide a list of the top ten actions you would take ON THE CURRENT FRAME. Ther should be exactly 10 different answers in the response.
    Only specify actions to take ON THE CURRENT FRAME.

    You can use the following functions:
    - actions.click(element_id, log_message) # click on an element
    - actions.input_text(element_id, text, clear_before_input, log_message) # Use clear_before_input=True to replace the text instead of appending to it. Never use this method on a combobox.
    - actions.scroll(direction, log_message) # scroll the page up or down. direction is either 'up' or 'down'.
    - actions.finish(did_succeed, output: dict, reason) # the task is complete with did_succeed=True or False, and a text reason. output is optional dictionary of output values if the task succeeded.
    element_id is always an integer, and is visible as a green label with white number around the TOP-LEFT CORNER OF EACH ELEMENT. Make sure to examine all green highlighted elements before choosing one to interact with.
    log_message is a short one sentence explanation of what the action does.
    Do not use keyword arguments, all arguments are positional.

    
    IMPORTANT: LOOK FOR CUES IN THE SCREENSHOTS TO SEE WHAT PARTS OF THE TASK ARE COMPLETED AND WHAT PARTS ARE NOT. FOR EXAMPLE, IF YOU ARE ASKED TO BUY A PRODUCT, LOOK FOR CUES THAT THE PRODUCT IS IN THE CART.
    Response format:

    Reasoning:
    Explanation for the next action, particularly focusing on interpreting the attached screenshot image.

    Code:
    ```python
    # variable definitions and non-webpage function calls are allowed
    ...
    # top ten webpage function calls, in any order. THEY SHOULD NOT BE IDENTICAL. 
    actions.func_name1(args..)
    actions.func_name2(args..)
    actions.func_name3(args..)
    actions.func_name4(args..)
    actions.func_name5(args..)
    actions.func_name6(args..)
    actions.func_name7(args..)
    actions.func_name8(args..)
    actions.func_name9(args..)
    actions.func_name10(args..)
    ```
    """
    # return SystemMessage(content=system_prompt)
    return system_prompt


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


def extract_code_many_actions(text):
    """
    Extracts all text in a string following the pattern "'\nCode:\n".
    """
    pattern = "\nCode:\n```python\n"
    start_index = text.find(pattern)
    if start_index == -1:
        raise Exception("Code not found")

    # Extract the text following the pattern, without the trailing "```"
    extracted_text = text[start_index + len(pattern) : -3]

    actions = extracted_text.split("\n")
    import pdb

    pdb.set_trace()

    return extracted_text


def get_gpt4_response(system_message, text_content, image_content):
    client = OpenAI(
        # This is the default and can be omitted
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": [{"type": "text", "text": system_message}],
                },
                {
                    "role": "user",
                    "content": [text_content, image_content],
                },
            ],
            # response_format={"type": "json_object"} if "json" in prompt.lower() else None,
            # temperature=temperature,
            max_tokens=4_096,
        )
    except Exception as e:
        logger.error(f"Failed to get response from OpenAI: {e}")
        raise e
    return response


def calcualte_next_action(task, observation):
    llm = get_llm()

    system_message = generate_system_message()
    user_message = generate_user_message(task, observation)

    try:
        # ai_message = llm([system_message, user_message])
        # Before subing out this `llm` for a standard gpt-4o call, see what it spits out
        ai_message = get_gpt4_response(system_message, user_message[0], user_message[1])
    except:
        # This sometimes solves the RPM limit issue
        logger.warning("Failed to get response from OpenAI, trying again in 30 seconds")
        exit(0)
        time.sleep(30)
        # ai_message = llm([system_message, user_message])

    # logger.info(f"AI message: {ai_message.content}")
    # code_to_execute = extract_code(ai_message.content)

    # Extract code for many actions
    # command_options = extract_code_many_actions(ai_message.choices[0].message.content)
    pattern = r"actions\.\w+\([^()]*\)"
    # Find all matches in the text

    matches = re.findall(pattern, ai_message.choices[0].message.content)
    import pdb

    pdb.set_trace()

    return code_to_execute


def get_task_status(observation):
    if observation.env_state.has_successfully_completed:
        return TASK_STATUS.SUCCESS
    elif observation.env_state.has_failed:
        return TASK_STATUS.FAILED
    else:
        return TASK_STATUS.IN_PROGRESS


def act(url, task, max_actions=40, **kwargs):
    task = Task(task=task, args=kwargs)

    browser = BrowserEnv(headless=False)
    observation = browser.reset(url)

    for i in range(max_actions):
        action = calcualte_next_action(task, observation)
        observation = browser.step(action, observation.marked_elements)
        task_status = get_task_status(observation)
        if task_status in [TASK_STATUS.SUCCESS, TASK_STATUS.FAILED]:
            return task_status, observation.env_state.output

    logger.warning(f"Reached {i} actions without completing the task.")
    return TASK_STATUS.FAILED, observation.env_state.output
