import base64
import random
from enum import Enum
import json
import time
import logging
from pywebagent.env.browser import BrowserEnv
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


def generate_system_message(observation):

    is_number = lambda s: s.replace(".", "", 1).isdigit() if s else False
    ids_of_elements_with_text = [
        _k
        for _k, _v in observation.marked_elements.items()
        if _v["text"] and not is_number(_v["text"])
    ]
    ids_to_specify = random.sample(
        ids_of_elements_with_text, min(10, len(ids_of_elements_with_text))
    )
    id_string = ", ".join(
        [
            f"id {_id} is {observation.marked_elements[_id]['text']}"
            for _id in ids_to_specify
        ]
    )

    system_prompt = f"""
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
    element_id is always an integer, and is visible as a green label with white number around the TOP-LEFT CORNER OF EACH ELEMENT.
    For example, {id_string}.
    Make sure to examine all green highlighted elements before choosing one to interact with.
    
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
    print(system_prompt)
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

    system_message = generate_system_message(observation)
    user_message = generate_user_message(task, observation, num_history)

    try:
        ai_message = llm([system_message, user_message])
    except:
        # This sometimes solves the RPM limit issue
        logger.warning("Failed to get response from OpenAI, trying again in 30 seconds")
        time.sleep(30)
        ai_message = llm([system_message, user_message])

    logger.info(f"AI message: {ai_message.content}")
    import pdb

    pdb.set_trace()

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
        action = calculate_next_action(task, observation, num_history)
        observation = browser.step(action, observation.marked_elements)
        task_status = get_task_status(observation)
        if task_status in [TASK_STATUS.SUCCESS, TASK_STATUS.FAILED]:
            return task_status, observation.env_state.output

    logger.warning(f"Reached {i} actions without completing the task.")
    return TASK_STATUS.FAILED, observation.env_state.output
