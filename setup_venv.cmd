@echo off

set PYTHON_EXE=C:/path/to/your/python.exe

echo Creating the virtual environment
call %PYTHON_EXE% -m venv .venv

echo Activating the virtual environment
call .venv/Scripts/activate

echo Installing poetry
call pip install poetry
call poetry --version

echo Press any key to exit...
pause > nul
