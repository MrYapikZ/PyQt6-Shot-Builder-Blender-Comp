import json
import os


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
        existing_data = {}
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    existing_data = {}

        existing_data.update(data)

        with open(file_path, 'w') as f:
            json.dump(existing_data, f, indent=4)
