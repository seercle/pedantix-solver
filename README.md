# pedantix-solver

## Description

## Setup

1. Clone the repository:
    ```bash
    git clone https://github.com/seercle/pedantix-solver.git
    cd pedantix-solver
    ```

2. Create a virtual environment:
    ```bash
    python -m venv venv
    ```

3. Activate the virtual environment:
    ```bash
    source venv/bin/activate
    ```

4. Setup the environment:
    ```bash
    pip install -r ./requirements.txt \
    && playwright install
    ```

## Usage (WARNING: You will need about 2.5GiB of storage and RAM to run this)

1. Create the json wikipedia tree (once)

    ```bash
    python tree.py
    ```

2. Solve pedantix (everytime you want to run it)
    ```bash
    python solver.py
    ```
