import json 
from typing import Callable, Any

# from chromadb import Collection
from pydantic import BaseModel, Field
from utils.query_parsing import ParsedQuery
# from agents.researcher_data import ResearchReportData
# from components.chroma_ddg import (
#     ChromaDDG,
#     CollectionDoesNotExist,
#     get_vectorstore_using_openai_api_key,
# )
# from components.llm import get_prompt_llm_chain
# from utils.helpers import (
#     PRIVATE_COLLECTION_PREFIX,
#     PRIVATE_COLLECTION_USER_ID_LENGTH,
#     get_timestamp,
# )
from utils.prepare import get_logger # DEFAULT_COLLECTION_NAME
# from utils.query_parsing import ParsedQuery
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
logger = get_logger()


# class ScheduledQueries(BaseModel):
#     queue_: list[ParsedQuery] = Field(default_factory=list)

#     def add_to_front(self, query: ParsedQuery) -> None:
#         """Add a query to the top of the queue. This query will be executed next."""
#         self.queue_.append(query)

#     def add_to_back(self, query: ParsedQuery) -> None:
#         """Add a query to the bottom of the queue. This query will be executed last."""
#         self.queue_.insert(0, query)

#     def pop(self) -> ParsedQuery | None:
#         """Pop the next query from the queue. Returns None if the queue is empty."""
#         try:
#             return self.queue_.pop()
#         except IndexError:
#             return None

#     def __len__(self) -> int:
#         return len(self.queue_)

#     def __bool__(self) -> bool:
#         return bool(self.queue_)
# from langchain_community.vectorstores import Chroma

# AgentDataDict = dict[str, JSONishDict]  # e.g. {"hs_data": {"links": [...], "blah": 3}}
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
        self.model = self.embedding_model()
        self.vectorstore = self.chromadb_load()
        self.original_question = original_question
        


    def chromadb_load(self):
        # chroma_client = chromadb.HttpClient(host='localhost', port=8000) 
        hugging_vectorstore = Chroma(persist_directory="./chroma_db6", embedding_function=self.model)  
        return hugging_vectorstore

    def embedding_model(self, process = 'cpu'):
        # Embedding 모델 불러오기 - 개별 환경에 맞는 device로 설정
        model_name = "upskyy/bge-m3-Korean"
        model_kwargs = {
            # "device": "cuda"
            # "device": "mps"
            "device": process
        }
        encode_kwargs = {"normalize_embeddings": True}
        hugging_embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs=model_kwargs,
            encode_kwargs=encode_kwargs,)
        return hugging_embeddings


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

