### setup virtual environment and packages
virtualenv venv
source venv/bin/activate
pip install -r backend/requirements.txt 


### set variables in `.env`
touch backend/.env
```.env

```


python3 backend/database/init/init_db.py
python3 backend/database/init/populate_problems.py
python3 backend/database/init/populate_contests.py

### Flask backend
python3 backend/app.py

### frontend
python3 custom_server.py