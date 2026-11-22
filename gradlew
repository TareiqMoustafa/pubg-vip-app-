#!/usr/bin/env sh
APP_HOME=$(pwd)
if command -v gradle >/dev/null 2>&1; then
    exec gradle "$@"
fi
echo "Gradle CLI not found in PATH" >&2
exit 1
