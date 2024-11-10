from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, get_buffer_string
from utils.type_utils import PairwiseChatHistory


def msg_list_chat_history_to_string(
    msg_list: list[BaseMessage],
    human_prefix="Human",
    ai_prefix="AI",
) -> str:
    """
    Convert a list of messages to a string such as 'Human: hi\nAI: Hi!\n...'
    """
    return get_buffer_string(msg_list, human_prefix, ai_prefix)

def pairwise_chat_history_to_msg_list(
    chat_history: PairwiseChatHistory,
) -> list[BaseMessage]:
    """Convert a pairwise chat history to a list of messages."""

    msg_list = []
    for human_msg, ai_msg in chat_history:
        msg_list.append(HumanMessage(content=human_msg))
        msg_list.append(AIMessage(content=ai_msg))
    return msg_list