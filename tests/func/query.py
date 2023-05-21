import time

import responses
from promptops import settings, settings_store
from promptops.ui import selections, prompts
from promptops.query import query
from unittest import mock
import os


@responses.activate
def test_generated():
    settings.endpoint = "http://localhost:8080"
    responses.post(settings.endpoint + "/feedback", json={"status": "ok"})
    responses.post(
        settings.endpoint + "/version", json={"update_required": False, "message": None, "latest_version": "0.1.test"}
    )
    responses.post(settings.endpoint + "/embeddings", json={"embeddings": [0.0] * 1536})
    responses.post(settings.endpoint + "/query", json={"suggestions": [{"script": "echo 'test'"}]})
    responses.post(settings.endpoint + "/explain", json={"explanation": "test"})

    from promptops.main import entry_alias
    import sys

    with mock.patch.object(settings_store, "load") as mock_load, mock.patch.object(
        settings_store, "is_changed", return_value=False
    ), mock.patch.object(os, "get_terminal_size") as mock_get_terminal_size, mock.patch.object(
        selections.UI, "input"
    ) as mock_ui_input, mock.patch.object(
        prompts, "confirm_command"
    ) as mock_confirm_command, mock.patch.object(
        query, "run"
    ) as mock_run:
        mock_load.return_value = None
        mock_get_terminal_size.return_value = os.terminal_size((80, 24))

        def respond_to_input(*args, **kwargs):
            time.sleep(0.2)
            return 0

        mock_ui_input.side_effect = respond_to_input
        mock_confirm_command.side_effect = lambda *args, **kwargs: kwargs.get("default", args[0])
        mock_run.return_value = (0, "test")
        sys.argv = ["um", "say test"]
        entry_alias()
        assert mock_run.call_count == 1
