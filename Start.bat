@echo off
echo Installation des dépendances...
pip install -r requirements.txt

echo Lancement de CXS-Search...
python CXS-search.py

pause
