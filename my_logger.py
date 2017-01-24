__author__ = 'd-kovacevic'
import logging

logger = logging.getLogger(" ")
logger.setLevel(logging.DEBUG)

handler = logging.FileHandler('route_monitor.log')
console = logging.StreamHandler()

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
console.setFormatter(formatter)

handler.setLevel(logging.INFO)
console.setLevel(logging.INFO)

logger.addHandler(handler)
logger.addHandler(console)