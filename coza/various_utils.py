import pickle
import json
import os
import signal
import configparser
import argparse
import logging
import string
import random
from datetime import datetime
from functools import wraps
import errno
from logging.handlers import RotatingFileHandler


def makedirs(path):
    try:
        os.makedirs(path)
    except Exception as e:
        return False
    return True


def save_as_pickle(obj, path, flag_make_path=True, opt="wb"):
    if flag_make_path:
        makedirs(os.path.dirname(path))
    with open(path, opt) as f:
        pickle.dump(obj, f)


def load_from_pickle(path, opt="rb"):
    with open(path, opt) as f:
        return pickle.load(f)


def load_from_json_file(path=None):
    """
    Load param
    """
    if path:
        with open(path, "rt") as f:
            param_dict = json.load(f)
    else:
        raise Exception("There is no param_path")

    return param_dict


def get_date_time_prefix():
    prefix = datetime.now().strftime("%Y%m%d_%H%M%S")
    return prefix


def id_generator(size=8, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def generate_id_with_date():
    result = "{}_{}".format(get_date_time_prefix(), id_generator())
    return result


def print_metric(**kwargs):
    for key, val in kwargs.items():
        print("{}: {}".format(key, val))


def generateLogger(file_path, logger_name=None, max_file_size=5242880, formatter='[%(levelname)s|%(filename)s:%(lineno)s] %(asctime)s > %(message)s'):
    """
    5242880 = 5*1024*1024
    """

    if logger_name is None:
        file_name, file_ext = os.path.splitext(file_path)
        logger_name = os.path.basename(file_name)

    logger_file_path = file_path
    logger = logging.getLogger(logger_name)
    formatter = logging.Formatter(
        formatter)
    fileHandler = logging.FileHandler(logger_file_path)
    streamHandler = logging.StreamHandler()
    rotatingFileandler = RotatingFileHandler(
        logger_file_path, mode='a', maxBytes=max_file_size,
        backupCount=2, encoding=None, delay=0)

    fileHandler.setFormatter(formatter)
    streamHandler.setFormatter(formatter)

    logger.addHandler(fileHandler)
    logger.addHandler(streamHandler)
    logger.addHandler(rotatingFileandler)
    logger.setLevel(logging.DEBUG)

    return logger


class TimeoutError(Exception):
    pass


def timeout(seconds=10, error_message=os.strerror(errno.ETIME)):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wraps(func)(wrapper)

    return decorator


def get_config(config_path, mode='development'):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode", help="mode [production|development] Default: development")
    args = parser.parse_args()

    if args.mode == 'production':
        mode = 'production'
    config = configparser.ConfigParser()
    config.read(config_path)
    cfg = config[mode]

    return cfg
