"""Runtime guards shared by the Awamoku launch descriptions."""

import fcntl
import os
import socket
import tempfile
from pathlib import Path


_LOCK_HANDLES = {}
_TRUE_VALUES = {"1", "true", "yes", "on"}


def claim_single_instance(context, ros_domain_id, use_endpoint, ros_ip):
    """Prevent duplicate Awamoku bringups before child nodes are started."""
    domain_id = ros_domain_id.perform(context)
    lock_path = Path(tempfile.gettempdir()) / f"awamoku_ros_domain_{domain_id}.lock"
    lock_handle = lock_path.open("w", encoding="utf-8")

    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        lock_handle.close()
        raise RuntimeError(
            f"Awamoku is already running for ROS_DOMAIN_ID={domain_id}. "
            "Stop the existing ros2 launch process with Ctrl+C before starting another one."
        ) from error

    lock_handle.write(f"{os.getpid()}\n")
    lock_handle.flush()
    _LOCK_HANDLES[str(lock_path)] = lock_handle

    endpoint_enabled = use_endpoint.perform(context).strip().lower() in _TRUE_VALUES
    if endpoint_enabled:
        _assert_port_available(ros_ip.perform(context), 10000)

    return []


def _assert_port_available(host, port):
    """Fail before launching nodes when another Unity TCP endpoint owns the port."""
    bind_host = host.strip() or "0.0.0.0"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((bind_host, port))
        except OSError as error:
            raise RuntimeError(
                f"Unity TCP endpoint port {bind_host}:{port} is already in use. "
                "Stop the existing Awamoku launch before starting a new one."
            ) from error
