import os
import sys
import time
import gevent
import traceback

triggers = {}
operations = {}

class Logging(type(sys)):
    CRITICAL = 50
    FATAL = CRITICAL
    ERROR = 40
    WARNING = 30
    WARN = WARNING
    INFO = 20
    DEBUG = 10
    NOTSET = 0

    def __init__(self, *args, **kwargs):
        self.level = self.__class__.INFO
        self.__set_error_color = lambda: None
        self.__set_warning_color = lambda: None
        self.__set_debug_color = lambda: None
        self.__reset_color = lambda: None
        if hasattr(sys.stderr, 'isatty') and sys.stderr.isatty():
            if os.name == 'nt':
                import ctypes
                SetConsoleTextAttribute = ctypes.windll.kernel32.SetConsoleTextAttribute
                GetStdHandle = ctypes.windll.kernel32.GetStdHandle
                self.__set_error_color = lambda: SetConsoleTextAttribute(GetStdHandle(-11), 0x04)
                self.__set_warning_color = lambda: SetConsoleTextAttribute(GetStdHandle(-11), 0x06)
                self.__set_debug_color = lambda: SetConsoleTextAttribute(GetStdHandle(-11), 0x002)
                self.__reset_color = lambda: SetConsoleTextAttribute(GetStdHandle(-11), 0x07)
            elif os.name == 'posix':
                self.__set_error_color = lambda: sys.stderr.write('\033[31m')
                self.__set_warning_color = lambda: sys.stderr.write('\033[33m')
                self.__set_debug_color = lambda: sys.stderr.write('\033[32m')
                self.__reset_color = lambda: sys.stderr.write('\033[0m')

    @classmethod
    def getLogger(cls, *args, **kwargs):
        return cls(*args, **kwargs)

    def basicConfig(self, *args, **kwargs):
        self.level = int(kwargs.get('level', self.__class__.INFO))
        if self.level > self.__class__.DEBUG:
            self.debug = self.dummy

    def log(self, level, fmt, *args, **kwargs):
        sys.stderr.write('%s - [%s] %s\n' % (level, time.ctime()[4:-5], fmt % args))

    def dummy(self, *args, **kwargs):
        pass

    # pylint: disable=method-hidden
    def debug(self, fmt, *args, **kwargs):
        self.__set_debug_color()
        self.log('DEBUG', fmt, *args, **kwargs)
        self.__reset_color()

    def info(self, fmt, *args, **kwargs):
        self.log('INFO', fmt, *args)

    def warning(self, fmt, *args, **kwargs):
        self.__set_warning_color()
        self.log('WARNING', fmt, *args, **kwargs)
        self.__reset_color()

    def warn(self, fmt, *args, **kwargs):
        self.warning(fmt, *args, **kwargs)

    def error(self, fmt, *args, **kwargs):
        self.__set_error_color()
        self.log('ERROR', fmt, *args, **kwargs)
        self.__reset_color()

    def exception(self, fmt, *args, **kwargs):
        self.error(fmt, *args, **kwargs)
        self.error(traceback.format_exc().replace("%", "%%"))

    def critical(self, fmt, *args, **kwargs):
        self.__set_error_color()
        self.log('CRITICAL', fmt, *args, **kwargs)
        self.__reset_color()

class Plugin(object):
    def __init__(self, name, typ):
        if name in globals():
            raise NameError("%s is already imported: %s" % (name, globals()[name]))
        self.name = name
        self.typ = typ
        path = list(sys.path)
        sys.path.insert(0, os.path.join('.', typ))
        self._ = __import__(name)
        sys.path[:] = path

    def wrap(self, *args, **kwargs):
        def f():
            try:
                return self._.call(*args, **kwargs)
            except:
                logging.exception("%s %s errored" % (self.typ, self.name))
            return False
        return f

class Trigger(Plugin):
    def __init__(self, name, onchange=False, reverse=False):
        Plugin.__init__(self, name, "triggers")
        self.onchange = onchange
        self.reverse = reverse

        self.last_state = None
    
    def register(self, *args, **kwargs):
        self._.register(*args, **kwargs)

    def wrap(self, *args, **kwargs):
        ff = Plugin.wrap(self, *args, **kwargs)
        def f():
            state = ff()
            if not self.onchange:
                if state == -1: # error
                    logging.debug("%s %s %s returned error state" % (
                      self.name, args, kwargs,  
                    ))
                    result = False
                else:
                    result = not state if self.reverse else state
            elif self.last_state == None:
                result = False
            elif self.last_state != state and state != self.reverse:
                # if changed, return True when state = True
                # or when state = False and reverse = True
                result = True
            else:
                result = False
            self.last_state = state
            return result
        return f
    

class Operation(Plugin):
    def __init__(self, name):
        Plugin.__init__(self, name, "operations")
    
    def wrap(self, *args, **kwargs):
        ff = Plugin.wrap(self, *args, **kwargs)
        def f(info_only=False):
            if info_only:
                return self.name, args, kwargs
            return ff()
        return f

class Smart(object):
    def __init__(self, poll_interval=60):
        self.rules = __import__("config").rules
        self.poll_interval = poll_interval
    
    def evaluate(self, rule):
        logging.debug("evaluating rule \"%s\"" % rule.name)
        rule.do()

    def run(self):
        while True:
            for rule in self.rules:
                # skip rule that are event triggered
                if not rule.has_registered:
                    self.evaluate(rule)
            gevent.sleep(self.poll_interval)


class Rule(object):
    def __init__(self, name):
        self.name = name
        self.triggers = {}
        self.operations = {}
        self.has_registered = False
    
    def do(self):
        do = True
        for t in self.triggers:
            if not self.triggers[t]():
                logging.debug("rule terminated at trigger \"%s\"" % t)
                do = False
                break
        if do:
            logging.info("rule \"%s\" passed" % self.name)
            for o in self.operations:
                name, args, kwargs = self.operations[o](info_only=True)
                logging.debug("execute %s %s %s" % (
                    name, args, kwargs,
                ))
                r = self.operations[o]()
                if r != None:
                    logging.debug("execute %s returned: %s" % (
                        name, r,
                    ))

    def add_trigger(self, name, t):
        suffix = ""
        cnt = 0
        while name+suffix in self.triggers:
            suffix = "_%d" % cnt
            cnt = cnt + 1
        self.triggers[name+suffix] = t

    def If(self, name, *args, **kwargs):
        self.add_trigger(name, Trigger(name).wrap(*args, **kwargs))
        return self

    def Not(self, name, *args, **kwargs):
        self.add_trigger("not_"+name, Trigger(name, reverse=True).wrap(*args, **kwargs))
        return self
    
    def Once(self, name, *args, **kwargs):
        self.add_trigger("once_"+name, Trigger(name, onchange=True).wrap(*args, **kwargs))
        return self

    def OnceNot(self, name, *args, **kwargs):
        self.add_trigger("oncenot_"+name, Trigger(name, onchange=True, reverse=True).
            wrap(*args, **kwargs))
        return self

    def On(self, name, *args):
        self.has_registered = True
        Trigger(name).register(lambda: self._real_callback(name), *args)
        return self

    def _real_callback(self, name, *args):
        logging.info("trigger \"%s\" invokes evalution of rule \"%s\" " % (name, self.name))
        return self.do()

    def Then(self, name, *args, **kwargs):
        suffix = ""
        cnt = 0
        while name+suffix in self.operations:
            suffix = "_%d" % cnt
            cnt = cnt + 1
        self.operations[name+suffix] = Operation(name).wrap(*args, **kwargs)
        return self

logging = Logging('logging')

if __name__ == "__main__":
    try:
        Smart(60).run()
    except KeyboardInterrupt:
        logging.debug("exiting...")

