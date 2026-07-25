#!/usr/bin/env bash
set -eo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

source /opt/ros/humble/setup.bash
source "${project_root}/awamoku_ws/install/setup.bash"
set -u

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-30}"

node_list="$(ros2 node list)"
if [[ -z "${node_list}" ]]; then
    echo "No ROS 2 nodes found for ROS_DOMAIN_ID=${ROS_DOMAIN_ID}."
    exit 1
fi

echo "ROS 2 nodes (count name):"
printf '%s\n' "${node_list}" | sort | uniq -c

duplicates="$(printf '%s\n' "${node_list}" | sort | uniq -cd || true)"
if [[ -n "${duplicates}" ]]; then
    echo
    echo "Duplicate node names detected. Stop the extra launch process before running Unity."
    exit 2
fi
