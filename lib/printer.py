from termcolor import colored
from gtts import gTTS
from playsound import playsound
from lib.help import LONG_HELP, ONELINE_HELP

class Printer:
    @staticmethod
    def print_to_user(text, raw_text = "", option = {}):
        print(text)
        if (option.get("audio")):
            if raw_text:
                play_text(raw_text, option.get("audio"))
            else:
                play_text(text, option.get("audio"))
            
    @staticmethod
    def print_bot_response(bot_name, res, option = {}):
        Printer.print_to_user(f"\033[92m\033[1m{bot_name}\033[95m\033[0m: {res}", res, option)

    @staticmethod
    def print_long_help(option = {}):
        Printer.print_to_user(LONG_HELP, LONG_HELP, option)

    @staticmethod
    def print_oneline_help(option = {}):
        Printer.print_to_user(ONELINE_HELP, ONELINE_HELP, option)
        
    @staticmethod
    def session_init(context):
        if context.config.verbose:
            Printer.print_info(f"Activating: {context.title} (model={context.llm_model.name()}, temperature={context.temperature}, max_token={context.llm_model.max_token()})")
        else:
            Printer.print_info(f"Activating: {context.title}")

    @staticmethod
    def print_info(text):
        print(colored(text, "blue"))


def play_text(text, lang):
    audio_obj = gTTS(text=text, lang=lang, slow=False)
    audio_obj.save("./output/audio.mp3")
    playsound("./output/audio.mp3")
        
