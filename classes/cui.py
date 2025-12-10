from classes.config import Config
import time


class cui:

    def __init__(self, config_data_instance : Config):
        self._verbose_mode = config_data_instance.config_data.get("system", {}).get("debuging", {}).get("verbose_mode", False)
    
    def print(self, message: str, type: str = "info"):

        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        if type == "info" or type == "INFO":
            print(f"{current_time} [INFO]: {message}")
        elif type == "error" or type == "ERROR":
            print(f"{current_time} [ERROR]: {message}")
        elif type == "success" or type == "SUCCESS":
            print(f"{current_time} [SUCCESS]: {message}")
        elif type == "verbose" or type == "VERBOSE":
            if self._verbose_mode:
                print(f"{current_time} [VERBOSE]: {message}")
        elif type == "warning" or type == "WARNING":
            print(f"{current_time} [WARNING]: {message}")