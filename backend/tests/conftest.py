import asyncio

import pytest
import pytest_asyncio
from beanie import init_beanie
from mongomock_motor import AsyncMongoMockClient

from app.database import DOCUMENT_MODELS


@pytest_asyncio.fixture
async def db():
    client = AsyncMongoMockClient()
    await init_beanie(database=client.tenderproof_test, document_models=DOCUMENT_MODELS)
    yield
