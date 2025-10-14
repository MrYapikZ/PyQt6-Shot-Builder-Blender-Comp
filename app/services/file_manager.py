import os
import re
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
    def combine_paths(*args: str, mkdir: bool = False) -> Path:
        path = Path(*args)
        if mkdir:
            path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def generate_png_comp(project_code: str, project_path: str, ep: str, seq: str, shot: str, file_type: str,
                          export_type: str) -> tuple:
        return os.path.join(project_path, f"{ep}", f"{ep}_{seq}", f"{ep}_{seq}_{shot}",
                            export_type), f"{project_code}_{ep}_{seq}_{shot}_{export_type}_####.{file_type}"

    @staticmethod
    def add_version_to_filename(file_path: str, version: int) -> str:
        base, ext = os.path.splitext(file_path)
        return f"{base}_v{version:03d}{ext}"

    @staticmethod
    def get_latest_version(progress_dir: str, shot_prefix: str, ext: str = ".blend") -> tuple[str, int, str] | tuple[
        None, int, str]:
        if shot_prefix.lower().endswith(ext.lower()):
            shot_prefix = shot_prefix[:-len(ext)]

        pattern = re.compile(rf"^{re.escape(shot_prefix)}_v(\d+){re.escape(ext)}$")
        latest_version = -1
        latest_file = None

        for filename in os.listdir(progress_dir):
            match = pattern.match(filename)
            if match:
                version = int(match.group(1))
                if version > latest_version:
                    latest_version = version
                    latest_file = filename

        # Compute next version number
        next_version = latest_version + 1
        next_name = f"{shot_prefix}_v{next_version:03d}{ext}"

        # Return path of latest file (if any), current version number, and next filename
        if latest_file:
            return os.path.join(progress_dir, next_name), next_version, next_name
        else:
            # No files found, start at v000
            next_name = f"{shot_prefix}_v000{ext}"
            return None, -1, next_name
