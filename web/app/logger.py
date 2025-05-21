import logging

def setup_logger():
    logger = logging.getLogger("ebay_search")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    fh = logging.FileHandler("server.log")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger