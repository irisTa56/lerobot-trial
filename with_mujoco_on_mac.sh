#!/usr/bin/env bash

SCRIPT_PATH="$1"

# MuJoCo requires the Python shared library to be accessible.
libdir="$(python -c 'import sysconfig; print(sysconfig.get_config_var("LIBDIR"))')"
DYLD_LIBRARY_PATH="$libdir:$DYLD_LIBRARY_PATH" mjpython "$SCRIPT_PATH"
