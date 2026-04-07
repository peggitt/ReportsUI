#STARTS REPORTS PORTAL
cd ./Apex/RepotsUI/
source myenv/bin/activate
cd ./Core/
nohup python3.10 manage.py runserver 0.0.0.0:7010 &
