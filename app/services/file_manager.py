import os
from pathlib import Path


class FileManager:
    @staticmethod
    def get_project_path(project_code: str) -> str:
        return os.path.join("/mnt", project_code)

    @staticmethod
    def generate_shot_path(project_path: str, production: str, division: str, ep: str, seq: str, shot: str) -> str:
        shot_path = os.path.join(project_path, production, division, f"{ep}", f"{ep}_{seq}",
                                 f"{ep}_{seq}_{shot}")
        os.makedirs(shot_path, exist_ok=True)
        return shot_path

    @staticmethod
    def generate_file_name(project_code: str, ep: str, seq: str, shot: str, division: str, extension: str) -> str:
        return f"{project_code}_{ep}_{seq}_{shot}_{division}.{extension}"

    @staticmethod
    def combine_paths(*args: str) -> Path:
        return Path(*args)

    @staticmethod
    def generate_png_comp(project_code: str, project_path: str, ep: str, seq: str, shot: str, file_type: str) -> str:
        return os.path.join(project_path, f"{ep}", f"{ep}_{seq}", f"{ep}_{seq}_{shot}", file_type,
                            f"{project_code}_{ep}_{seq}_{shot}_render_####.{file_type}")
