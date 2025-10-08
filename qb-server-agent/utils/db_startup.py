import os
from pathlib import Path

def start_db_file(app):
    database_path_env = os.getenv("DATABASE_PATH")

    if not database_path_env:
        base_path = Path(os.getenv("APPDATA", Path.home())) / "qb_server_agent"
        base_path.mkdir(parents=True, exist_ok=True)
        database_path = base_path / "qb_agent.db"
    else:
        database_path = Path(database_path_env).expanduser().resolve()

        if database_path.suffix == "":
            database_path = database_path.with_suffix(".db")

        database_path.parent.mkdir(parents=True, exist_ok=True)

    database_uri = f"sqlite:///{database_path}"

    app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    print(f"Database configured in: {database_path}")
