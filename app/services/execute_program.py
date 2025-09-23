import subprocess
import tempfile

class ExecuteProgram:
    @staticmethod
    def blender_execute(blender_path: str, script: str):
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tmp:
                tmp.write(script)
                tmp_path = tmp.name

            subprocess.run([blender_path, "--background", "--python", tmp_path])
            return True
        except subprocess.CalledProcessError as e:
            print(f"An error occurred while executing Blender: {e}")
            return False