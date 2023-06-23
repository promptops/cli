DEFAULT_ENDPOINT = "https://cli.promptops.com"

endpoint: str = DEFAULT_ENDPOINT
request_explanation: bool = True
model: str = "accurate"
history_context: int = 0
corrections_db_path = "~/.promptops/corrections.db"
history_db_path = "~/.promptops/history.db"
user_id_path = "~/.promptops/user_id"
index_history: bool = False
user_index_root = "~/.promptops/index"
temp_history_file = "~/.promptops/temp_history"
gen_commit_message = None
