from promptops.query.suggest_next import suggest_next_suffix, suggest_next_suffix_near, suggest_next_gpt, deduplicate, pretty_result
from .choice import Choice


def instant_choices(n: int = 4) -> list[Choice]:
    options = deduplicate(suggest_next_suffix(n // 2) + suggest_next_suffix_near(n // 2))
    return [Choice("command", pretty_result(option), option) for option in options]


def generated_choices() -> list[Choice]:
    options = deduplicate(suggest_next_gpt())
    return [Choice("command", pretty_result(option), option) for option in options]
