import json


class JSONManager:
    @staticmethod
    def read_json(file_path):
        try:
            with open(file_path, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def write_json(file_path, data):
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)
