# Update paths accordingly, like "<path to virtual env>/Lib/site-packages"
$path = '.venv/Lib/site-packages'

pyinstaller .\src\panhunt.py -F --clean -i .\dionach.ico --paths=$path