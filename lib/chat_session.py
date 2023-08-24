import random
import re
from datetime import datetime

from termcolor import colored

from lib.chat_config import ChatConfig
from lib.dbs.pinecone import DBPinecone
from lib.history.base import ChatHistory
from lib.history.memory_storage import ChatMemoryHistory
from lib.llms.models import get_llm_model_from_manifest
from lib.manifest import Manifest
from lib.utils.log import create_log_dir, save_log

"""
ChatSession represents a chat session with a particular AI agent.
The key is the identifier of the agent.
The manifest specifies behaviors of the agent.
"""


class ChatSession:
    def __init__(self, config: ChatConfig, manifest_key: str = "GPT"):
        self.config = config
        self.manifest_key = manifest_key

        self.set_manifest()

        self.time = datetime.now()
        self.userName = self.manifest.username()
        self.botName = self.manifest.botname()
        self.title = self.manifest.title()
        self.intro = self.manifest.get("intro")
        self.actions = self.manifest.actions()
        self.temperature = self.manifest.temperature()

        self.intro_message = None
        memory_history = ChatMemoryHistory()
        self.history = ChatHistory(memory_history)
        # init log dir
        create_log_dir(manifest_key)

        # Load the model name and make it sure that we have required keys
        llm_model = get_llm_model_from_manifest(self.manifest)
        self.set_llm_model(llm_model)

        # Load the prompt, fill variables and append it as the system message
        self.prompt = self.manifest.prompt_data(config.manifests)
        if self.prompt:
            self.history.append({"role": "system", "content": self.prompt})

        # Prepare embedded database index
        self.vector_db = self.get_vector_db()

        # Load functions file if it is specified
        self.functions = self.manifest.functions()
        if self.functions and self.config.verbose:
            print(colored(self.functions, "cyan"))

        self.function_call = None
        self.next_llm_call = False

    def set_manifest(self):
        manifest_data = self.config.get_manifest_data(self.manifest_key)
        self.manifest = Manifest(
            manifest_data if manifest_data else {}, self.manifest_key
        )

    def set_llm_model(self, llm_model):
        if llm_model.check_api_key(self.config):
            self.llm_model = llm_model
        else:
            print(
                colored(
                    "You need to set "
                    + llm_model.get("api_key")
                    + " to use this model. ",
                    "red",
                )
            )
        if self.config.verbose:
            print(colored(f"Model = {self.llm_model.name()}", "cyan"))

    def get_manifest_attr(self, key):
        return self.manifest.get(key)

    def get_vector_db(self):
        # Todo: support other vector dbs.
        embeddings = self.manifest.get("embeddings")
        if embeddings:
            table_name = embeddings.get("name")
            try:
                return DBPinecone.factory(table_name, self.config)
            except Exception as e:
                print(colored(f"Pinecone Error: {e}", "yellow"))

    """
    Append a message to the chat session, specifying the role ("user", "system" or "function").
    In case of a function message, the name specifies the function name.
    """

    def append_message(self, role: str, message: str, name=None):
        self.history.append_message(role, message, name)

    def append_user_question(self, message: str):
        self.append_message("user", message)
        if self.vector_db:
            articles = self.vector_db.fetch_related_articles(
                self.llm_model.max_token() - 500
            )
            assert (
                self.history.get_data(0, "role") == "system"
            ), "Missing system message"
            self.history.set(
                0,
                {
                    "role": "system",
                    "content": re.sub("\\{articles\\}", articles, self.prompt, 1),
                },
            )

    def save_log(self):
        save_log(self.manifest_key, self.history.messages(), self.time)

    def set_intro(self):
        if self.intro:
            self.intro_message = self.intro[random.randrange(0, len(self.intro))]
            self.append_message("assistant", self.intro_message)

    """
    Let the LLM generate a responce based on the messasges in this session.
    Return values:
        role: "assistent"
        res: message
        function_call: json representing the function call (optional)
    """

    def generate_response(self):
        # res = None
        # function_call = None
        # role = "assistant"
        return self.llm_model.generate_response(
            self.history.messages(), self.manifest, self.config.verbose
        )

    def call_llm(self):
        (role, res, function_call) = self.generate_response()

        self.set_function_call(function_call)
        if role and res:
            self.append_message(role, res)
            self.save_log()

        return res

    # for next call
    def set_function_call(self, function_call):
        if function_call:
            function_call.set_action(self.actions)
        self.function_call = function_call

        self.next_llm_call = False

    def set_next_llm_call(self, value):
        self.function_call = None
        self.next_llm_call = value

    def should_call_function_call(self):
        return self.function_call is not None and self.function_call.should_call()

    def should_call_llm(self):
        return self.next_llm_call

    def has_emit(self):
        return (
            self.function_call
            and self.function_call.function_action
            and self.function_call.function_action.has_emit()
        )

    def get_emit_data(self):
        return self.function_call.get_emit_data()

    def process_function_call(self, runtime, verbose=False):
        (
            function_message,
            function_name,
            role,
            should_next_call_llm,
        ) = self.function_call.process_function_call(
            self.manifest, self.history, runtime, verbose
        )
        self.set_next_llm_call(should_next_call_llm)
        return (function_message, function_name, role)
