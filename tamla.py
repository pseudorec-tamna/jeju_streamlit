import os
from typing import Any

from langchain.chains import LLMChain
from utils.prepare import DEFAULT_OPENAI_API_KEY, WEATHER_KEY, get_logger
from utils.chat_state import ChatState
from utils.type_utils import OperationMode
from utils.prompts import ( 
    JUST_CHAT_PROMPT,
)
from components.llm import get_prompt_llm_chain
from utils.lang_utils import pairwise_chat_history_to_msg_list
from agents.greeting_quick import get_greeting_chat_chain
from agents.question_quick import get_question_chat_chain
from agents.hyeonwoo import get_hw_response
from utils.type_utils import ChatMode
from langchain.memory import ConversationBufferWindowMemory

logger = get_logger()

default_vectorstore = None  # can move to chat_state


# memory management

def get_bot_response(
    chat_state: ChatState,
):
    chat_mode_val = (
        chat_state.chat_mode.value
    )
    if chat_mode_val == ChatMode.JUST_CHAT_COMMAND_ID.value:
        chat_chain = get_prompt_llm_chain(
            JUST_CHAT_PROMPT,
            llm_settings=chat_state.bot_settings,
            api_key=chat_state.google_api_key,
            callbacks=chat_state.callbacks,
            stream=True,
        )
        
        answer = chat_chain.invoke(
            {
                "message": chat_state.message,
                "chat_history": pairwise_chat_history_to_msg_list(
                    chat_state.chat_history 
                ),
            }
        )
        return {"answer": answer}
    elif chat_mode_val == ChatMode.JUST_CHAT_GREETING_ID.value:
        return get_greeting_chat_chain(chat_state)
    elif chat_mode_val == ChatMode.CHAT_HW_ID.value:
        return get_hw_response(chat_state)
    elif chat_mode_val == ChatMode.CHAT_QUESTION_ID.value:
        return get_question_chat_chain(chat_state)
    else:
        # Should never happen
        raise ValueError(f"Invalid chat mode: {chat_state.chat_mode}")


if __name__ == "__main__":
    chat_history = []

    response = get_bot_response(
        ChatState(
            operation_mode=OperationMode.CONSOLE,
            chat_history=chat_history,
            google_api_key=DEFAULT_OPENAI_API_KEY,
            user_id=None,  # would be set to None by default but just to be explicit
        )
    )
