# How to run locally

1) Go to code directory
```
cd schoselwette
```

2) Copy `wette/config-sqlite-sample.py` to `wette/config.py`
```
cp wette/config-sqlite-sample.py wette/config.py
```

3) Edit `wette/config.py` and replace placeholder values (only first time after cloning)

4) Create a virtual environment
```
python3 -m venv venv
source venv/bin/activate
```

5) Install dependencies
```
pip install -r requirements.txt
```

6) Create/migrate the database
```
flask --app wette db upgrade
```

7) Start the app
```
./run.sh
```

# How to run with Docker (production)

```
docker build -t schoselwette .
docker run -p 8000:8000 \
  -e SQLALCHEMY_DATABASE_URI="mysql+pymysql://user:pass@host/db" \
  -e SECRET_KEY="..." \
  -e PASSWORD_SALT="..." \
  schoselwette
```
