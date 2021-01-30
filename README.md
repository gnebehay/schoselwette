# How to run locally

1) Go to code directory
```
cd code
```

2) Copy `wette/config-<sqlite||mysql>-sample.py` to config.py
```
cp wette/config-<sqlite||mysql>-sample.py wette/config.py
```

3) Edit `wette/config.py` file and replace `<values>` (only first time after cloning repo)

4) Create a virtual environment
```
python3 -m venv venv
```

5) Install dependencies
```
./setup.sh

```

6) Active virtual environment
```
./venv/bin/activate
```

7) Create database
```
wette/db_create.py
```

8) Start app
```
./run.py
```
