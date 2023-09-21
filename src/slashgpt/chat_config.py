import os
import sys
from typing import Optional

import google.generativeai as palm
import openai
import pinecone
from dotenv import load_dotenv

from slashgpt.llms.default_config import default_llm_engine_configs, default_llm_models
from slashgpt.llms.engine_factory import LLMEngineFactory

"""
ChatConfig is a singleton, which holds global states, including various secret keys
"""


class ChatConfig:
    def __init__(self, base_path: str, llm_models: Optional[dict] = None, llm_engine_configs: Optional[dict] = None):
        self.base_path = base_path
        # Load various keys from .env file
        load_dotenv()
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        if not self.OPENAI_API_KEY:
            print("OPENAI_API_KEY environment variable is missing from .env")
            sys.exit()
        self.EMBEDDING_MODEL = "text-embedding-ada-002"
        self.PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
        self.PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "")

        self.verbose = False

        # Initialize OpenAI and optinoally Pinecone and Palm
        openai.api_key = self.OPENAI_API_KEY
        if self.PINECONE_API_KEY and self.PINECONE_ENVIRONMENT:
            pinecone.init(api_key=self.PINECONE_API_KEY, environment=self.PINECONE_ENVIRONMENT)

        self.llm_models = llm_models if llm_models else default_llm_models
        self.llm_engine_configs = llm_engine_configs if llm_engine_configs else default_llm_engine_configs
        # engine
        if self.llm_engine_configs:
            LLMEngineFactory.llm_engine_configs = self.llm_engine_configs

    # for llm
    def has_environment_value(self, key: str):
        return os.getenv(key, None) is not None
