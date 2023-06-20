import os
import shutil
import subprocess
import tempfile
import time


def edit_with_vim(content) -> str:
    if not shutil.which("vim"):
        print("vim seems to be unavailable on your system")
        time.sleep(.5)
        return content

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
        temp_file.write(content.encode('utf-8'))
        temp_file.flush()

        subprocess.call(["vim", temp_file.name])

        with open(temp_file.name, 'r') as modified_file:
            modified_content = modified_file.read()

    os.remove(temp_file.name)

    return modified_content
