def non_empty_input(prompt: str) -> str:
    result = ""
    while result == "":
        result = input(prompt).strip()
    return result
