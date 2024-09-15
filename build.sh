#!/usr/bin/env bash

# Update paths accordingly, like "<path to virtual env>/Lib/site-packages"

PATHS=".venv/Lib/site-packages"

pyinstaller src/panhunt.py -F --clean -i dionach.ico --paths="${PATHS}"

