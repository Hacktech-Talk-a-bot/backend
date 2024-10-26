# backend

## Install Poetry (if not already installed)

### For linux:
```sh
curl -sSL https://install.python-poetry.org | python3 -
```

##### Navigate to your project directory
```sh
cd path/to/your/project
```

##### Install dependencies and create a virtual environment
```sh
poetry install
```

##### Activate the virtual environment
```sh
poetry shell
```

### For windows:
1. In `etup_venv.cmd` edit the path to your python executable `set PYTHON_EXE=C:/path/to/your/python.exe`
2. Run `setup_venv.cmd`

##### Activate the virtual environment
```sh
.venv\Scripts\activate
```

##### Deactivate the virtual environment
```sh
deactivate
```

## Run project
```sh
poetry run start
```