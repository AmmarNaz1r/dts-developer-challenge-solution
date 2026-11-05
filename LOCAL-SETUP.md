# Run the Caseworker Task Manager locally

## Requirements

- Python 3.11 or newer
- pip

## Windows PowerShell

Open PowerShell in the project folder (the folder containing \`main.py\` and \`requirements.txt\`), then run:

\`\`\`powershell
python -m venv .venv
.\\.venv\\Scripts\\python.exe -m pip install --upgrade pip
.\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt
.\\.venv\\Scripts\\python.exe -m uvicorn main:app --reload
\`\`\`

If \`py\` is available, you can use \`py -3 -m venv .venv\` for the first command. The project uses the base Uvicorn package rather than optional \`[standard]\` extras to avoid compiling optional PyYAML dependencies on Windows.

## macOS / Linux

\`\`\`bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
\`\`\`

## Open the application

- Application: http://127.0.0.1:8000
- Interactive API docs: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/health

The local SQLite database (\`tasks.db\`) is created automatically. Tasks remain saved between runs on that computer.

## Run tests

Stop the development server with Ctrl+C, then run:

\`\`\`powershell
.\\.venv\\Scripts\\python.exe -m pytest
\`\`\`

On macOS/Linux, with the virtual environment activated, run \`python -m pytest\`. Tests use an in-memory database and do not modify your local \`tasks.db\`.

## Stop the server

Return to the terminal running Uvicorn and press Ctrl+C.

## Troubleshooting

- If Python is not recognised, install Python 3.11+ and reopen PowerShell.
- If a package is missing, rerun the install command using the virtual environment's Python executable.
- If port 8000 is occupied, add \`--port 8001\` to the Uvicorn command and open http://127.0.0.1:8001.
