import json 
from typing import Callable, Any

from pydantic import BaseModel, Field
from utils.query_parsing import ParsedQuery
from utils.prepare import get_logger
from utils.type_utils import (
    COLLECTION_USERS_METADATA_KEY,
    AccessCodeSettings,
    AccessRole,
    BotSettings,
    CallbacksOrNone,
    ChatMode,
    CollectionPermissions,
    CollectionUserSettings,
    JSONishDict,
    OperationMode,
    PairwiseChatHistory,
    Props
)
from langchain_core.documents import Document
from langchain.memory import ConversationBufferMemory
from langchain_community.embeddings.huggingface import HuggingFaceEmbeddings
from utils.client import get_vectordb
logger = get_logger()
vdb_instance = None
vdb = get_vectordb()

import chromadb
from langchain_chroma import Chroma

class ChatState:
    def __init__(
        self,
        *,
        operation_mode: OperationMode,
        # vectorstore: ChromaDDG,
        is_community_key: bool = False,
        parsed_query: ParsedQuery | None = None,
        chat_history: PairwiseChatHistory | None = None,
        chat_and_command_history: PairwiseChatHistory | None = None,
        sources_history: list[list[str]] | None = None,
        callbacks: CallbacksOrNone = None,
        add_to_output: Callable | None = None,
        bot_settings: BotSettings | None = None,
        user_id: str | None = None,  # NOTE: should switch to "" instead of None
        google_api_key: str | None = None,
        # scheduled_queries: ScheduledQueries | None = None,
        access_role_by_user_id_by_coll: dict[str, dict[str, AccessRole]] | None = None,
        access_code_by_coll_by_user_id: dict[str, dict[str, str]] | None = None,
        uploaded_docs: list[Document] | None = None,
        price_range:list[int] | None = None,
        selected_tags:list[str] | None = None,
        memory = ConversationBufferMemory(return_messages=True, memory_key="chat_history"),
        multi_turn_amount: int = 0,
        recommend_term:bool = False,
        info_location: str = "",
        info_menuplace: list[str] =[''],
        info_keyword: list[str] = [''],
        info_business_type: list[str] = [''],
        chat_basic_mode: str | None = None,
        flag_trend: str | None = None,
        flag: str | None = None,
        flag_eng: str | None = None,
        query_rewrite: str | None = None,
        original_question: str = ''
        # session_data: AgentDataDict | None = None,  # currently not used (agent
        # data is stored in collection metadata)
    ) -> None: 
        self.operation_mode = operation_mode
        self.is_community_key = is_community_key
        self.parsed_query = parsed_query or ParsedQuery()
        self.chat_history = chat_history or []  # tuple of (user_message, bot_response)
        self.chat_history_all = chat_and_command_history or []
        self.sources_history = sources_history or []  # used only in Streamlit for now
        self.callbacks = callbacks
        self.add_to_output = add_to_output or (
            lambda *args: print(args[0], end="", flush=True)
        )
        self.bot_settings = bot_settings or BotSettings()
        self.user_id = user_id
        self.google_api_key = google_api_key
        # self.scheduled_queries = scheduled_queries or ScheduledQueries()
        self._access_role_by_user_id_by_coll = access_role_by_user_id_by_coll or {}
        self._access_code_by_coll_by_user_id = access_code_by_coll_by_user_id or {}
        self.uploaded_docs = uploaded_docs or []
        self.price_range = price_range or []
        self.selected_tags = selected_tags or []
        self.multi_turn_amount = multi_turn_amount
        self.info_location = info_location
        self.info_menuplace = info_menuplace
        self.info_keyword = info_keyword
        self.info_business_type = info_business_type
        self.recommend_term = recommend_term
        self.memory = memory
        self.chat_basic_mode = chat_basic_mode
        self.flag_trend = flag_trend
        self.flag = flag
        self.flag_eng = flag_eng
        self.model = vdb.embedding
        self.vectorstore = vdb.hugging_vectorstore
        self.query_rewrite = query_rewrite
        self.original_question = original_question
        
    @property
    def chat_mode(self) -> ChatMode:
        return self.parsed_query.chat_mode

    @property
    def message(self) -> str:
        return self.parsed_query.message

    @property
    def search_params(self) -> Props:
        return self.parsed_query.search_params or {}

    def update(self, **kwargs) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)

