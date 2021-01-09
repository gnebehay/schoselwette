# How to run locally

1) Go to code directory
```
cd code
```

1) Copy config-sample.py to config.py
```
cp wette/config-sample.py wette/config.py
```

1) Create a virtual environment
```
python3 -m venv venv
```

1) Install dependencies
```
./setup.sh

```

1) Active virtual environment
```
./venv/bin/activate
```

1) Create database
```
wette/db_create.py
```

1) Start app
```
./run.py
```
