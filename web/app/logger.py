import logging
from config import settings


def setup_logger(name: str = "ebay_search"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    fh = logging.FileHandler(settings.SERVER_LOG_FILE)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger
