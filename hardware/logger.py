from machine import enable_irq, disable_irq

INFO = 0
WARNING = 1
ERROR = 2
UNKNOWN = -1

class Logger:
    FILENAME = None
    TIME_FUNC = None
    _logger = None
    cache = []
    
    @staticmethod
    def get_logger():
        if Logger._logger is None:
            if Logger.FILENAME is None or Logger.TIME_FUNC is None:
                raise ValueError("Logger is not ready")
            Logger._logger = Logger(Logger.FILENAME, Logger.TIME_FUNC)
        return Logger._logger
    
    def __init__(self, filename, time_func):
        try:
            self._file = open(filename, "a+")
        except Exception as e:
            raise ValueError(f'Cannot open "{filename}"') from e
        self._time_func = time_func
        
    def log(self, *messages, level=UNKNOWN, delimiter=" "):
        msg = self._time_func() + " - "
        
        if level == INFO:
            msg += "INFO - "
        elif level == WARNING:
            msg += "WARNING - "
        elif level == ERROR:
            msg += "ERROR - "
        else:
            msg += "UNKNOWN - "
            
        for i, message in enumerate(messages):
            if i != 0:
                msg += delimiter
            msg += str(message)
            
        state = disable_irq()
        Logger.cache.append(msg)
        enable_irq(state)
        
        self._file.write(msg + "\n")
        self._file.flush()
        
    def info(self, *messages):
        self.log(*messages, level=INFO)
    
    def warning(self, *messages):
        self.log(*messages, level=WARNING)
    
    def error(self, *messages):
        self.log(*messages, level=ERROR)


