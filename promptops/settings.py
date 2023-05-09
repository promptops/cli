DEFAULT_ENDPOINT = "https://cli-development.promptops.com"


endpoint: str = DEFAULT_ENDPOINT
request_explanation: bool = True
model: str = "accurate"
history_context: int = 0
corrections_db_path = "~/.promptops/corrections.db"
history_db_path = "~/.promptops/history.db"
