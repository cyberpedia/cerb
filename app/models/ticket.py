from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum, Index
from sqlalchemy.orm import relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class TicketStatus(str, PyEnum):
    """Ticket status enum."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_USER = "waiting_for_user"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, PyEnum):
    """Ticket priority enum."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketCategory(str, PyEnum):
    """Ticket category enum."""
    CHALLENGE_ISSUE = "challenge_issue"
    PLATFORM_BUG = "platform_bug"
    ACCOUNT_ISSUE = "account_issue"
    QUESTION = "question"
    OTHER = "other"


class Ticket(Base):
    """Support ticket model for user inquiries."""
    
    __tablename__ = "tickets"
    
    __table_args__ = (
        Index("ix_tickets_status", "status"),
        Index("ix_tickets_user_id", "user_id"),
        Index("ix_tickets_created_at", "created_at"),
    )
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    # Ticket details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(Enum(TicketCategory), default=TicketCategory.QUESTION, nullable=False)
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN, nullable=False)
    priority = Column(Enum(TicketPriority), default=TicketPriority.MEDIUM, nullable=False)
    
    # Related challenge (optional)
    challenge_id = Column(String(36), ForeignKey("challenges.id"), nullable=True)
    
    # Assignment
    assigned_to = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="tickets")
    assignee = relationship("User", foreign_keys=[assigned_to])
    challenge = relationship("Challenge", back_populates="tickets")
    responses = relationship("TicketResponse", back_populates="ticket", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Ticket(id={self.id}, title={self.title}, status={self.status})>"


class TicketResponse(Base):
    """Response/comment on a support ticket."""
    
    __tablename__ = "ticket_responses"
    
    __table_args__ = (
        Index("ix_ticket_responses_ticket_id", "ticket_id"),
        Index("ix_ticket_responses_created_at", "created_at"),
    )
    
    id = Column(String(36), primary_key=True)
    ticket_id = Column(String(36), ForeignKey("tickets.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    # Response content
    content = Column(Text, nullable=False)
    is_internal = Column(String(1), default="N", nullable=False)  # Y/N - internal admin note
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    ticket = relationship("Ticket", back_populates="responses")
    user = relationship("User")
    
    def __repr__(self) -> str:
        return f"<TicketResponse(id={self.id}, ticket_id={self.ticket_id})>"
