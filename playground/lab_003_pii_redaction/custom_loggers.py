import logging


LOG_FORMAT = "[%(name)s] - %(levelname)s ->   %(message)s"
LOG_LEVEL = logging.DEBUG

DEFAULT_LOGGER = logging.getLogger("DEFAULT_DEBUG")
LLM_LOGGER = logging.getLogger("LLM_DEBUG")
WS_LOGGER = logging.getLogger("WS_DEBUG")

default_fmt = logging.Formatter(LOG_FORMAT)
default_handler = logging.StreamHandler()
default_handler.setFormatter(default_fmt)

DEFAULT_LOGGER.setLevel(LOG_LEVEL)
LLM_LOGGER.setLevel(LOG_LEVEL)
WS_LOGGER.setLevel(LOG_LEVEL)

DEFAULT_LOGGER.addHandler(default_handler)
LLM_LOGGER.addHandler(default_handler)
WS_LOGGER.addHandler(default_handler)

DEFAULT_LOGGER.propagate = False
LLM_LOGGER.propagate = False
WS_LOGGER.propagate = False
