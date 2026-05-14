from time import localtime
from logger import Logger

def get_current_time_str():
    t = localtime()
    return f"{t[0]:04}-{t[1]:02}-{t[2]:02} {t[3]:02}:{t[4]:02}:{t[5]:02}"

Logger.FILENAME = "log.txt"
Logger.TIME_FUNC = get_current_time_str

l = Logger.get_logger()
l.log("a", "b", 1000, level=INFO)
l.log("a", "b", 1000, level=WARNING)
l.info("LEONID")
l.warning("TYKHON")
l.error("VITALIY")

Logger.get_logger().error("WE ARE TUCKED")