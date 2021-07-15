@echo off
echo Checking Python version...
python --version 2>NUL
if errorlevel 1 goto errorNoPython
echo Python install looks good. Starting...
python do_rss.py
echo Process complete!
pause
goto :EOF
:errorNoPython
echo(
echo Error: You don't have Python 3 installed!!! Contact Adam!!!
pause