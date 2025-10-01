import time
import logging
import sys
import os

service = os.getenv("SERVICE_NAME", "testlogger")

logger = logging.getLogger(service)
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] [" + service + "] %(message)s"))
logger.addHandler(handler)

i = 0
while True:
    logger.info(f"Hello from {service} #{i}")
    i += 1
    time.sleep(2)