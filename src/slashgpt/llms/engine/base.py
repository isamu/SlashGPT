from abc import ABCMeta, abstractmethod
from typing import List, Optional

import tiktoken  # for counting tokens

from slashgpt.function.function_call import FunctionCall
from slashgpt.manifest import Manifest
from slashgpt.utils.print import print_warning


class LLMEngineBase(metaclass=ABCMeta):
    def __init__(self, llm_model):
        self.llm_model = llm_model

    @abstractmethod
    def chat_completion(self, messages: List[dict], manifest: Manifest, verbose: bool):
        pass

    def num_tokens(self, text: str):
        """Calculate the llm token of the text. Because this is for openai, override it if you use another language model."""
        model_name = self.llm_model.name() if self.llm_model.name().startswith("gpt-") else "gpt-3.5-turbo-0613"
        encoding = tiktoken.encoding_for_model(model_name)
        return len(encoding.encode(text))

    """
    Extract the Python code from the string if the agent is a code interpreter.
    Returns it in the "function call" format.
    """

    def _extract_function_call(self, last_message: dict, manifest: Manifest, res: str, is_openai: bool = False):
        if manifest.get("notebook"):
            lines = res.splitlines()
            codes: Optional[list] = None
            for key in range(len(lines)):
                if self.__is_code(lines, key, is_openai):
                    if codes is None:
                        codes = []
                    else:
                        break
                elif codes is not None:
                    codes.append(lines[key])
            if codes:
                return FunctionCall(
                    {
                        "name": "run_python_code",
                        "arguments": {"code": codes, "query": last_message["content"]},
                    },
                    manifest,
                )

            print_warning("Debug Message: no code in this reply")
        return None

    def __is_code(self, lines, key, is_openai: bool = False):
        if is_openai:
            if len(lines) == key + 1:  # last line has no next line.
                return lines[key][:3] == "```"
            else:
                if lines[key][:3] == "```":
                    return lines[key + 1].startswith("!pip") or lines[key + 1].startswith("from ") or lines[key + 1].startswith("import ")
            return False
        else:
            return lines[key][:3] == "```"
