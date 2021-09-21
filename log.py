import logging


def set_logger(name):
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.setLevel(logging.INFO)
    # logger.setLevel(logging.ERROR)
    logger.addHandler(handler)
    return logger
