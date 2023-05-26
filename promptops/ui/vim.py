import subprocess
import tempfile


def edit_with_vim(content) -> str:
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
        temp_file.write(content.encode('utf-8'))
        temp_file.flush()

        subprocess.call(["vim", temp_file.name])

        with open(temp_file.name, 'r') as modified_file:
            modified_content = modified_file.read()

    subprocess.call(["rm", temp_file.name])

    return modified_content
