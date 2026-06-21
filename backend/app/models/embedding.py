from app.models import Ticket
from sqlalchemy import BigInteger, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.db import Base

class TicketEmbedding(Base):
    __tablename__ = "ticket_embeddings"

    ticket_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tickets.id", ondelete="CASCADE"),
        primary_key=True
    )

    # nomic-embed-text-v1.5 has an embedding dimension of 768
    embedding: Mapped[list[float]] = mapped_column(Vector(768), nullable=False)

    # 1-to-1 relationship back to the Ticket
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="embedding")

    # Define the HNSW index using pgvector's cosing distance operator
    __table_args__ = (
        Index(
            "idx_ticket_embeddings_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"}
        ),
    )