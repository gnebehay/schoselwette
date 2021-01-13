# How to run locally

1) Edit `wette/config-<sqlite||mysql>-sample.py` file and replace `<values>` (only first time after cloning repo)

2) Copy `wette/config-<sqlite||mysql>-sample.py` to `wette/config.py` (only first time after cloning repo)
```
cp wette/config-mysql-sample.py wette/config.py
```

3) Create a virtual environment
```
python3 -m venv venv
```

4) Install dependencies (after cloning or pulling repo)
```
./setup.sh
```

5) Activate virtual environment
```
source ./venv/bin/activate
```

6) Create database (only first time after cloning repo)
```
wette/db_create.py
```

7) Start app
```
./run.sh
```
