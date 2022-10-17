class BotException(Exception):
    def __init__(self, *args):
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        if self.message:
            return f"BotError, {self.message}"
        else:
            return "BotError has been raised"


class BotTypeError(BotException, TypeError):
    pass


class BotKeyError(BotException, KeyError):
    pass
