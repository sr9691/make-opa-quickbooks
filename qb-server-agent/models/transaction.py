# api/models.py
from extensions import db
from datetime import datetime, UTC

class Transaction(db.Model):
    __tablename__ = 'transactions'

    transaction_id = db.Column(db.String, primary_key=True)
    identifier = db.Column(db.String, nullable=True)
    idempotency_key = db.Column(db.String, unique=True, nullable=True)
    timestamp = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String, nullable=True)  # pending, success, error, duplicate
    processing_time_ms = db.Column(db.Integer, nullable=True)
    qbxml_request = db.Column(db.Text, nullable=True)
    qbxml_response = db.Column(db.Text, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    error_code = db.Column(db.String, nullable=True)
    retry_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    def to_dict(self):
        """Helper para serializar o objeto como JSON."""
        return {
            "transaction_id": self.transaction_id,
            "identifier": self.identifier,
            "idempotency_key": self.idempotency_key,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "status": self.status,
            "processing_time_ms": self.processing_time_ms,
            "qbxml_request": self.qbxml_request,
            "qbxml_response": self.qbxml_response,
            "error_message": self.error_message,
            "error_code": self.error_code,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"<Transaction {self.transaction_id} - {self.status}>"
