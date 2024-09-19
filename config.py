import json

class Config:
    def __init__(self, config_file="config.json"):
        # Load the configuration and store each key as a class variable
        with open(config_file) as fo:
            json_config = json.load(fo)

        for key, value in json_config.items():
            setattr(self, key, value)

    def __str__(self):
        return '\n'.join([v for v in vars(self)])

    def get(self, key, value=None):
        return getattr(self, key, value)

    def __getattr__( self, name):
        return None

if __name__ == "__main__":
    config = Config()
    print(config)

    print(config.calendar)
    print(config.calendars)

    print(config.get("calendars"))
    print(config.get("dne"))
    print(config.get("dne", []))