import os
from datetime import datetime, timezone

from utils.chat_state import ChatState
from utils.helpers import (
    DB_COMMAND_HELP_TEMPLATE,
    DB_CREATED_AT_TIMESTAMP_FORMAT,
    PRIVATE_COLLECTION_FULL_PREFIX_LENGTH,
    PRIVATE_COLLECTION_PREFIX,
    PRIVATE_COLLECTION_PREFIX_LENGTH,
    PRIVATE_COLLECTION_USER_ID_LENGTH,
    format_nonstreaming_answer,
    parse_timestamp,
)
from utils.prepare import (
    get_logger,
)

logger = get_logger()


def get_main_owner_user_id(collection_name: str) -> str | None:
    """
    Get the user ID of the native owner of a collection. If the collection is public,
    return None.
    """
    if collection_name.startswith(PRIVATE_COLLECTION_PREFIX):
        return collection_name[
            PRIVATE_COLLECTION_PREFIX_LENGTH:PRIVATE_COLLECTION_FULL_PREFIX_LENGTH
        ]


def get_user_facing_collection_name(user_id: str | None, collection_name: str) -> str:
    """
    Get the user-facing name of a collection by removing the internal prefix
    containing the user ID, if any. The prefix is removed only if the user ID
    matches the one in the collection name.
    """
    # Old collections: u-abcdef<name>, new collections: u-abcdef-<name>
    return (
        collection_name[PRIVATE_COLLECTION_FULL_PREFIX_LENGTH:].lstrip("-")
        if collection_name.startswith(PRIVATE_COLLECTION_PREFIX)
        and user_id == get_main_owner_user_id(collection_name)
        else collection_name
    )

