@echo off
cd /d "%~dp0"
python -u serve.py --host 127.0.0.1 --port 4174
