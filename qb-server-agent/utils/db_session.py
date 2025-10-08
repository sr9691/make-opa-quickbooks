# utils/db_session.py
import logging
from contextlib import contextmanager
from extensions import db

@contextmanager
def db_session_scope():
    try:
        yield db.session
        db.session.commit()
    except Exception as e:
        logging.exception("Database transaction rolled back due to error")
        db.session.rollback()
        raise
    finally:
        db.session.close()
