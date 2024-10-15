from typing import Any
from uuid import UUID
from langchain_openai import ChatOpenAI
from utils.type_utils import BotSettings, CallbacksOrNone
from langchain_core.language_models import BaseChatModel
from utils.prepare import (
    LLM_REQUEST_TIMEOUT,
    MODEL_NAME
)
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompt_values import ChatPromptValue
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from utils.helpers import DELIMITER, MAIN_BOT_PREFIX
from langchain_core.callbacks import BaseCallbackHandler
from utils.lang_utils import msg_list_chat_history_to_string
from streamlit.delta_generator import DeltaGenerator
from langchain_core.outputs import ChatGenerationChunk, GenerationChunk, LLMResult
from utils.streamlit.helpers import fix_markdown
from langchain_google_genai import ChatGoogleGenerativeAI


class CallbackHandlerDDGStreamlit(BaseCallbackHandler):
    def __init__(self, container: DeltaGenerator, end_str: str = ""):
        self.container = container
        self.buffer = ""
        self.end_str = end_str
        self.end_str_printed = False

    def on_llm_new_token(
        self,
        token: str,
        *,
        chunk: GenerationChunk | ChatGenerationChunk | None = None,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        self.buffer += token
        self.container.markdown(fix_markdown(self.buffer))

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Run when LLM ends running."""
        if self.end_str:
            self.end_str_printed = True
            self.container.markdown(fix_markdown(self.buffer + self.end_str))

def get_llm_with_gemini(
    settings: BotSettings, api_key: str | None = None, callbacks: CallbacksOrNone = None
) -> BaseChatModel:
    llm = ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        google_api_key=api_key,  # 여기에 실제 API 키를 입력하세요
        temperature=settings.temperature,
        request_timeout=LLM_REQUEST_TIMEOUT,
        streaming=True,
        callbacks=callbacks,
        verbose=True,  # tmp
    )
    return llm


def get_llm_with_callbacks(
    settings: BotSettings, api_key: str | None = None, callbacks: CallbacksOrNone = None
) -> BaseChatModel:
    """
    Returns a chat model instance (either AzureChatOpenAI or ChatOpenAI, depending
    on the value of IS_AZURE). In the case of AzureChatOpenAI, the model is
    determined by CHAT_DEPLOYMENT_NAME (and other Azure-specific environment variables),
    not by settings.model_name.
    """
    llm = ChatOpenAI(
        api_key=api_key or "",  # don't allow None, no implicit key from env
        model=settings.llm_model_name,
        temperature=settings.temperature,
        request_timeout=LLM_REQUEST_TIMEOUT,
        streaming=True,
        callbacks=callbacks,
        verbose=True,  # tmp
    )
    return llm

class CallbackHandlerDDGConsole(BaseCallbackHandler):
    def __init__(self, init_str: str = MAIN_BOT_PREFIX):
        self.init_str = init_str

    def on_llm_start(
        self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any
    ) -> None:
        print(self.init_str, end="", flush=True)

    def on_llm_new_token(self, token, **kwargs) -> None:
        print(token, end="", flush=True)

    def on_llm_end(self, *args, **kwargs) -> None:
        print()

    def on_retry(self, *args, **kwargs) -> None:
        print(f"ON_RETRY: \nargs = {args}\nkwargs = {kwargs}")

def get_llm(
    settings: BotSettings,
    api_key: str | None = None,
    callbacks: CallbacksOrNone = None,
    stream=False,
    init_str=MAIN_BOT_PREFIX,
) -> BaseChatModel:
    """
    Return a chat model instance (either AzureChatOpenAI or ChatOpenAI, depending
    on the value of IS_AZURE). If callbacks is passed, it will be used as the
    callbacks for the chat model. Otherwise, if stream is True, then a CallbackHandlerDDG
    will be used with the passed init_str as the init_str.
    """
    if callbacks is None:
        callbacks = [CallbackHandlerDDGConsole(init_str)] if stream else []
    return get_llm_with_gemini(settings, api_key, callbacks)


def get_prompt_llm_chain(
    prompt: PromptTemplate,
    llm_settings: BotSettings,
    api_key: str | None = None,
    print_prompt=False,
    **kwargs,
):
    if not print_prompt:
        return prompt | get_llm(llm_settings, api_key, **kwargs) | StrOutputParser()

    def print_and_return(thing):
        if isinstance(thing, ChatPromptValue):
            print(f"PROMPT:\n{msg_list_chat_history_to_string(thing.messages)}")
        else:
            print(f"PROMPT:\n{type(thing)}\n{thing}")
        print(DELIMITER)
        return thing
    
    return (
        prompt
        | print_and_return
        | get_llm(llm_settings, api_key, **kwargs)
        | StrOutputParser()
    )


