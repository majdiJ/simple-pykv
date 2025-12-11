from classes.config import Config
import time


class cui:

    def __init__(self, config_data_instance : Config):
        self._verbose_mode = config_data_instance.config_data.get("system", {}).get("debuging", {}).get("verbose_mode", False)
        self.RED = "\x1b[31m"
        self.GREEN = "\x1b[32m"
        self.YELLOW = "\x1b[33m"
        self.BLUE = "\x1b[34m"
        self.RESET = "\x1b[0m"
    
    def print(self, message: str, type: str = "info"):

        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        if type == "info" or type == "INFO":
            print(f"{current_time} [INFO]: {message}")
        elif type == "error" or type == "ERROR":
            print(f"{self.RED}{current_time} [ERROR]: {message}{self.RESET}")
        elif type == "success" or type == "SUCCESS":
            print(f"{self.GREEN}{current_time} [SUCCESS]: {message}{self.RESET}")
        elif type == "verbose" or type == "VERBOSE":
            if self._verbose_mode:
                print(f"{self.BLUE}{current_time} [VERBOSE]: {message}{self.RESET}")
        elif type == "warning" or type == "WARNING":
            print(f"{self.YELLOW}{current_time} [WARNING]: {message}{self.RESET}")