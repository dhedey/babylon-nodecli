class BaseConfig:
    def __init__(self, settings: dict):
        for key, value in settings.items():
            setattr(self, key, value)

    def __iter__(self):
        class_variables = {key: value
                           for key, value in self.__class__.__dict__.items()
                           if not key.startswith('__') and not callable(value)}
        for attr, value in class_variables.items():
            if self.__getattribute__(attr):
                yield attr, self.__getattribute__(attr)
