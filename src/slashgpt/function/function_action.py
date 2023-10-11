import os
from urllib.parse import quote_plus, urlparse

from slashgpt.function.network import graphQLRequest, http_request
from slashgpt.utils.print import print_debug, print_error
from slashgpt.utils.utils import CallType


class FunctionAction:
    """It represents an action to take for the spcified function call (by LLM)"""

    def __init__(self, function_action_data: dict):
        """Use the factory classmethod to create an instance

        function_action_data(dict): the action data associated with the function name
        """
        self.__function_action_data = function_action_data

    @classmethod
    def factory(cls, function_action_data):
        """May create an instance if the function_action_data exists"""
        if function_action_data is None:
            return None
        return FunctionAction(function_action_data)

    def __get(self, key: str):
        return self.__function_action_data.get(key)

    def has_emit(self):
        """Returns if the action type is emit"""
        return self.__call_type() == CallType.EMIT

    def emit_method(self):
        """Returns the "emit_method" property of emit_data"""
        return self.__get("emit_method")

    def emit_data(self, arguments: dict):
        """Returns the data to emit by replacing all {arg}"""

        def format(value):
            if isinstance(value, str):
                return value.format(**arguments)
            elif isinstance(value, dict):
                return {x: format(value.get(x)) for x in value}
            return value

        data = self.__get("emit_data")
        return {x: format(data.get(x)) for x in data}

    def call_api(self, arguments: dict, base_dir: str, verbose: bool):
        """Execute a function appropriately for each CallType"""
        type = self.__call_type()
        if type == CallType.REST:
            appkey_value = self.__get_appkey_value() or ""

            return http_request(
                self.__get("url"),
                self.__get("method"),
                self.__function_action_data.get("headers", {}),
                appkey_value,
                arguments,
                verbose,
            )
        if type == CallType.GRAPHQL:
            appkey_value = self.__get_appkey_value() or ""
            return graphQLRequest(
                url=self.__get("url"),
                headers=self.__function_action_data.get("headers", {}),
                appkey_value=appkey_value,
                arguments=arguments,
                verbose=verbose,
            )

        if type == CallType.DATA_URL:
            return self.__read_dataURL_template(
                base_dir,
                self.__get("template"),
                self.__get("mime_type"),
                self.__get("message"),
                arguments,
                verbose,
            )

        if type == CallType.MESSAGE_TEMPLATE:
            return self.__get("message").format(**arguments)
        return "Success"

    def __call_type(self):
        type = self.__get("type")
        if type:
            if type == "rest":
                return CallType.REST
            if type == "graphQL":
                return CallType.GRAPHQL
            if type == "data_url":
                return CallType.DATA_URL
            if type == "message_template":
                return CallType.MESSAGE_TEMPLATE
            if type == "emit":
                return CallType.EMIT

    def __read_dataURL_template(self, base_dir: str, template_file_name: str, mime_type: str, message_template: str, arguments: dict, verbose: bool):
        _mime_type = mime_type or ""
        with open(f"{base_dir}/{template_file_name}", "r") as f:
            template = f.read()
            if verbose:
                print_debug(template)
            data = template.format(**arguments)
            dataURL = f"data:{_mime_type};charset=utf-8,{quote_plus(data)}"
            return message_template.format(url=dataURL)

    def __get_appkey_value(self):
        appkey = self.__get("appkey")
        url = self.__get("url")

        if appkey:
            appkey_value = os.getenv("SLASH_GPT_ENV_" + appkey, "")

            # check domain
            param = appkey_value.split(",")
            if len(param) == 2:
                parsed_url = urlparse(url)
                if param[0] != parsed_url.netloc:
                    print_error(f"Invalid appkey domain {appkey} in .env file.")
                    return
                appkey_value = param[1]

            if not appkey_value:
                print_error(f"Missing {appkey} in .env file.")
            return appkey_value
