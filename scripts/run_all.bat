@echo off
cd /d "C:\Users\willi\projs\papertrading\swingbot"
echo %date% %time% - Starting SwingBot >> "C:\Users\willi\projs\papertrading\swingbot\logs\scheduler.log"
"C:\Users\willi\AppData\Local\Programs\Python\Python311\python.exe" scripts\run_strategies.py >> "C:\Users\willi\projs\papertrading\swingbot\logs\scheduler.log" 2>&1
"C:\Users\willi\AppData\Local\Programs\Python\Python311\python.exe" scripts\run_bot.py --paper >> "C:\Users\willi\projs\papertrading\swingbot\logs\scheduler.log" 2>&1
"C:\Users\willi\AppData\Local\Programs\Python\Python311\python.exe" scripts\dashboard.py >> "C:\Users\willi\projs\papertrading\swingbot\logs\scheduler.log" 2>&1
echo %date% %time% - Done >> "C:\Users\willi\projs\papertrading\swingbot\logs\scheduler.log"
