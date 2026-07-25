import fcntl
import socket
import tempfile
from pathlib import Path

import pytest

from awamoku_game import launch_guards


class StubSubstitution:
    def __init__(self, value: str) -> None:
        self.value = value

    def perform(self, _context) -> str:
        return self.value


def test_claim_single_instance_rejects_a_second_launch() -> None:
    domain_id = "9899"
    lock_path = Path(tempfile.gettempdir()) / f"awamoku_ros_domain_{domain_id}.lock"
    substitutions = [
        StubSubstitution(domain_id),
        StubSubstitution("false"),
        StubSubstitution("0.0.0.0"),
    ]

    try:
        assert launch_guards.claim_single_instance(None, *substitutions) == []
        with pytest.raises(RuntimeError, match="already running"):
            launch_guards.claim_single_instance(None, *substitutions)
    finally:
        lock_handle = launch_guards._LOCK_HANDLES.pop(str(lock_path), None)
        if lock_handle is not None:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
            lock_handle.close()


def test_port_guard_rejects_an_occupied_endpoint_port() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        occupied_port = server.getsockname()[1]
        with pytest.raises(RuntimeError, match="already in use"):
            launch_guards._assert_port_available("127.0.0.1", occupied_port)
