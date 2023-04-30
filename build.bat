@echo off

:: Update paths accordingly, like "<path to virtual env>/Lib/site-packages"
set path = ".venv/Lib/site-packages"

pyinstaller src/panhunt.py -F --clean -i dionach.ico --paths=%path% --hidden-import=appdirs --hidden-import=pyparsing