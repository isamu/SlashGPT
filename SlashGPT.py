#!/usr/bin/env python3
import platform
import re
if platform.system() == "Darwin":
    import readline # So that input can handle Kanji & delete
import json
from enum import Enum
from termcolor import colored

from lib.jupyter_runtime import PythonRuntime
from lib.chat_session import ChatSession
from lib.chat_config import ChatConfig
from lib.llms.models import llm_models, get_llm_model_from_key
from lib.printer import Printer

class InputStyle(Enum):
  HELP = 1
  TALK = 2
  SLASH = 3
  SAMPLE = 4

"""
utility functions for Main class
"""

manifests = {
    "main": {
        "manifests_dir": "manifests/main",
        "default_manifest_key": "dispatcher",
    },
    "rpg1": {
        "manifests_dir": "manifests/rpg1",
        "default_manifest_key": "bartender",
    },
    "zoo": {
        "manifests_dir": "manifests/zoo",
        "default_manifest_key": "monkey",
    },
    "roles1": {
        "manifests_dir": "manifests/roles1",
        "default_manifest_key": None,
    },
    "roles2": {
        "manifests_dir": "manifests/roles2",
        "default_manifest_key": None,
    },
};

"""
Main is a singleton, which process the input from the user and manage chat sessions.
"""
class Main:
    def __init__(self, config: ChatConfig, manifest_key: str):
        self.config = config

        self.exit = False
        self.runtime = PythonRuntime("./output/notebooks")
        self.switch_context(manifest_key)

    """
    switchContext terminate the current chat session and start a new.
    The key specifies the AI agent.
    """
    def switch_context(self, manifest_key: str, intro: bool = True):
        if manifest_key is None:
            self.context = ChatSession(self.config)
            return
        if self.config.exist_manifest(manifest_key):
            self.context = ChatSession(self.config, manifest_key=manifest_key)
            if self.context.get_manifest_attr("notebook"):
                (result, _) = self.runtime.create_notebook(self.context.llm_model.name() )
                print(colored(f"Created a notebook: {result.get('notebook_name')}", "blue"))

            if intro:
                self.context.set_intro()
        else:            
            print(colored(f"Invalid slash command: {manifest_key}", "red"))

    def parse_question(self, question: str):
        key = question[1:].strip()
        commands = re.split('\s+', key)
        return (key, commands);
            
    def detect_input_style(self, question: str):
        (key, commands) = self.parse_question(question)
        if len(question) == 0:
            return InputStyle.HELP
        elif key[:6] == "sample":
            return InputStyle.SAMPLE
        elif question[0] == "/":
            return InputStyle.SLASH
        else:
            return InputStyle.TALK

    def display_oneline_help(self):
        Printer.print_oneline_help(self.print_option())

    def print_option(self): 
        return {"audio": self.config.audio}
        
    def process_sample(self, question: str):
        (key, commands) = self.parse_question(question)
        if commands[0] == "sample" and len(commands) > 1:
            sub_key = commands[1]
            sub_manifest_data = self.config.get_manifest_data(sub_key)
            if sub_manifest_data:
                sample = sub_manifest_data.get("sample")
                if sample:
                    print(sample)
                    return sample
            else:
                agents = self.context.get_manifest_attr("agents")
                if agents:
                    print("/sample {agent}: " +  ", ".join(agents))
                else:
                    print(colored(f"Error: No manifest named '{sub_key}'", "red"))
        elif key[:6] == "sample":
            sample = self.context.get_manifest_attr(key)
            if sample:
                print(sample)
                return sample
            print(colored(f"Error: No {key} in the manifest file", "red"))
        return None
            
    """
    If the question start with "/", process it as a Slash command.
    Otherwise, return (roleInput, question) as is.
    Notice that some Slash commands returns (role, question) as well.
    """
    def process_slash(self, question: str):
        (key, commands) = self.parse_question(question)
        if commands[0] == "help":
            if (len(commands) == 1):
                Printer.print_long_help(self.print_option())
                list = "\n".join(self.config.help_list())
                print(f"Agents:\n{list}")
            if (len(commands) == 2):
                manifest_data = self.config.get_manifest_data(commands[1])
                if (manifest_data):
                   print(json.dumps(manifest_data, indent=2))
        elif key == "bye":
            self.runtime.stop()
            self.exit = True;
        elif key == "verbose":
            self.config.verbose = self.config.verbose == False
            print(f"Verbose Mode: {self.config.verbose}")
        elif commands[0] == "audio":
            if len(commands) == 1:
                if self.config.audio:
                    self.config.audio = None
                else:
                    self.config.audio = "en"
            elif commands[1] == "off":
                self.config.audio = None
            else:
                self.config.audio = commands[1]
            print(f"Audio mode: {self.config.audio}")
        elif key == "prompt":
            if len(self.context.messages) >= 1:
                print(self.context.messages[0].get("content"))
            if self.config.verbose and self.context.functions:
                print(self.context.functions)
        elif key == "history":
            print(json.dumps(self.context.messages, indent=2))
        elif key == "functions":
            if self.context.functions:
                print(json.dumps(self.context.functions, indent=2))
        elif commands[0] == "llm" or commands[0] == "llms":
            if len(commands) > 1 and llm_models.get(commands[1]):
                llm_model = get_llm_model_from_key(commands[1])
                self.context.set_llm_model(llm_model)
            else:
                print("/llm: " + ",".join(llm_models.keys()))
        elif key == "new":
            self.switch_context(self.context.manifest_key, intro = False)
        elif commands[0] == "switch":
            if len(commands) > 1 and manifests.get(commands[1]):
                m = manifests[commands[1]]
                self.config.load_manifests("./" + m["manifests_dir"])
                self.switch_context(m["default_manifest_key"])
            else:
                print("/switch {manifest}: " +  ", ".join(manifests.keys()))
        elif self.config.has_manifest(key):
                self.switch_context(key)
        else:
            print(colored(f"Invalid slash command: {key}", "red"))


    def process_llm(self):
        try:
            # Ask LLM to generate a response.
            (responseRole, res, function_call) = self.context.generate_response()

            if responseRole and res:
                Printer.print_bot_response(self.context.botName, res, self.print_option())

                self.context.append_message(responseRole, res)
                self.context.save_log()

            if function_call:
                (question, function_name) = self.process_function_call(function_call)
                if question:
                    role = "function" if function_name or self.context.skip_function_result() else "user"
                    
                    print(f"\033[95m\033[1mfunction({function_name}): \033[95m\033[0m{question}")
                    self.context.append_message(role, question, function_name)
                    if not self.context.skip_function_result():
                        self.process_llm()

        except Exception as e:
            print(colored(f"Exception: Restarting the chat :{e}","red"))
            self.switch_context(self.context.manifest_key)
            if self.config.verbose:
                raise

    """
    the main loop
    """    
    def start(self):
        while not self.exit:
            self.talk_with_input()
            
    def talk_with_input(self):
        form = None
        question = input(f"\033[95m\033[1m{self.context.userName}: \033[95m\033[0m").strip()
        if question[:1] == "`":
            print(colored("skipping form", "blue"))
            question = question[1:]
        else:
            form = self.context.get_manifest_attr("form")

        mode = self.detect_input_style(question)
        if mode == InputStyle.HELP:
            self.display_oneline_help()
        elif mode == InputStyle.SLASH:
            self.process_slash(question)
        else:
            if mode == InputStyle.SAMPLE:
                question = self.process_sample(question)
            if question and form:
                question = form.format(question = question)

            if question:
                self.context.append_message("user", question)
                self.process_llm()
            
    def process_function_call(self, function_call):
        function_message = None
        function_name = function_call.name()
        arguments = function_call.arguments()
                
        print(colored(json.dumps(function_call.data(), indent=2), "blue"))
        '''
        if isinstance(arguments, str):
            params = arguments
        else:
            params = ','.join(f"{key}={function_call["arguments"][key]}" for key in function_call.arguments.keys())
        print(colored(f"Function: {function_name}({params})", "blue"))
        '''
        if function_name:
            action = self.context.get_action(function_name)
            if action:
                if action.is_switch_context():
                    self.switch_context(action.get_manifest_key(arguments),  intro = False)
                    function_name = None # Without name, this message will be treated as user prompt.
                    
                # call external api or some
                function_message = action.call_api(arguments, self.config.verbose)
            else:
                if self.context.get_manifest_attr("notebook"):
                    # Python code from llm
                    if function_name == "python" and isinstance(arguments, str):
                        print(colored("python function was called", "yellow"))
                        arguments = {
                            "code": arguments,
                            "query": self.context.messages[-1]["content"]
                        }
                    function = getattr(self.runtime, function_name)
                else:
                    # Python code from resource file
                    function = self.context.get_module(function_name) # python code
                if function:
                    if isinstance(arguments, str):
                        (result, message) = function(arguments)
                    else:
                        (result, message) = function(**arguments)
                    if message:
                        # Embed code for the context
                        self.context.append_message("assistant", message)
                    function_message = self.python_result(result)
                else:
                    print(colored(f"No function {function_name} in the module", "red"))
        return (function_message, function_name)

    def python_result(self, result):
        if isinstance(result, dict):
            result = json.dumps(result)
        result_form = self.context.get_manifest_attr("result_form")
        if result_form:
            return result_form.format(result = result)
        return result


        
if __name__ == '__main__':
    config = ChatConfig("./manifests/main")
    Printer.print_oneline_help()
    main = Main(config, 'dispatcher')
    main.start()
