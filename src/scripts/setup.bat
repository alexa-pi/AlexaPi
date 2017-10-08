echo off
title AlexaPi for Windows Installation
cls

SET mypath=%~dp0
SET apath=%mypath:~0,-8%
SET path=%path%;%mypath%\swigwin-AlexaPi

echo -------------------------------------------
echo Welcome in AlexaPi installation for Windows
echo -------------------------------------------

echo Installing dependencies:

python -m pip install -r "%apath%requirements.txt"

pause
cls

cd %apath%

copy config.template.yaml config.yaml

echo ######################################################################################################
echo IMPORTANT NOTICE:
echo You HAVE TO set up Amazon keys in the config.yaml file now
echo ######################################################################################################
pause

start python.exe auth_web.py

echo =====
echo Done!
echo =====
pause
cls
echo ######################################################################################################
echo IMPORTANT NOTICE:
echo You may HAVE TO set up your system audio.
echo See on our wiki
echo ######################################################################################################
pause