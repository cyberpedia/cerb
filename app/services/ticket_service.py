"""
Ticket Service - Manages support tickets for user inquiries.
Allows users to ask "Is this broken?" and admins to respond.
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.ticket import Ticket, TicketResponse, TicketStatus, TicketPriority, TicketCategory
from app.services.notification_manager import NotificationManager


class TicketService:
    """Service for managing support tickets."""
    
    def __init__(self, db: AsyncSession, notification_manager: Optional[NotificationManager] = None):
        self.db = db
        self.notification_manager = notification_manager
    
    # ==================== Ticket CRUD ====================
    
    async def create_ticket(
        self,
        user_id: str,
        title: str,
        description: str,
        category: TicketCategory = TicketCategory.QUESTION,
        priority: TicketPriority = TicketPriority.MEDIUM,
        challenge_id: Optional[str] = None
    ) -> Ticket:
        """Create a new support ticket."""
        ticket = Ticket(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            description=description,
            category=category,
            priority=priority,
            challenge_id=challenge_id,
            status=TicketStatus.OPEN,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(ticket)
        await self.db.commit()
        await self.db.refresh(ticket)
        
        # Notify admins about new ticket
        if self.notification_manager:
            await self.notification_manager.notify_admins(
                f"New support ticket: {title}",
                f"User submitted a ticket in category: {category.value}"
            )
        
        return ticket
    
    async def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        """Get a ticket by ID with all responses."""
        result = await self.db.execute(
            select(Ticket)
            .options(
                selectinload(Ticket.user),
                selectinload(Ticket.assignee),
                selectinload(Ticket.challenge),
                selectinload(Ticket.responses).selectinload(TicketResponse.user)
            )
            .where(Ticket.id == ticket_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_tickets(
        self,
        user_id: str,
        status: Optional[TicketStatus] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Ticket]:
        """Get all tickets for a user."""
        query = select(Ticket).where(Ticket.user_id == user_id)
        
        if status:
            query = query.where(Ticket.status == status)
        
        query = query.order_by(desc(Ticket.created_at)).offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_all_tickets(
        self,
        status: Optional[TicketStatus] = None,
        priority: Optional[TicketPriority] = None,
        assigned_to: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Ticket]:
        """Get all tickets (admin view)."""
        query = select(Ticket).options(
            selectinload(Ticket.user),
            selectinload(Ticket.assignee)
        )
        
        if status:
            query = query.where(Ticket.status == status)
        if priority:
            query = query.where(Ticket.priority == priority)
        if assigned_to:
            query = query.where(Ticket.assigned_to == assigned_to)
        
        query = query.order_by(
            # Critical/High priority first
            Ticket.priority.in_([TicketPriority.CRITICAL, TicketPriority.HIGH]).desc(),
            desc(Ticket.created_at)
        ).offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def update_ticket(
        self,
        ticket_id: str,
        status: Optional[TicketStatus] = None,
        priority: Optional[TicketPriority] = None,
        assigned_to: Optional[str] = None
    ) -> Optional[Ticket]:
        """Update ticket status, priority, or assignment."""
        ticket = await self.get_ticket(ticket_id)
        if not ticket:
            return None
        
        if status:
            ticket.status = status
            if status == TicketStatus.RESOLVED:
                ticket.resolved_at = datetime.utcnow()
            elif status == TicketStatus.CLOSED:
                ticket.closed_at = datetime.utcnow()
        
        if priority:
            ticket.priority = priority
        
        if assigned_to is not None:
            ticket.assigned_to = assigned_to
        
        ticket.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(ticket)
        
        # Notify user of status change
        if self.notification_manager and status:
            await self.notification_manager.notify_user(
                ticket.user_id,
                f"Ticket updated: {ticket.title}",
                f"Status changed to: {status.value}"
            )
        
        return ticket
    
    # ==================== Ticket Responses ====================
    
    async def add_response(
        self,
        ticket_id: str,
        user_id: str,
        content: str,
        is_internal: bool = False
    ) -> TicketResponse:
        """Add a response to a ticket."""
        response = TicketResponse(
            id=str(uuid.uuid4()),
            ticket_id=ticket_id,
            user_id=user_id,
            content=content,
            is_internal="Y" if is_internal else "N",
            created_at=datetime.utcnow()
        )
        
        self.db.add(response)
        
        # Update ticket timestamp
        ticket = await self.get_ticket(ticket_id)
        if ticket:
            ticket.updated_at = datetime.utcnow()
            
            # Auto-update status if user responds to waiting ticket
            if not is_internal and ticket.status == TicketStatus.WAITING_FOR_USER:
                ticket.status = TicketStatus.IN_PROGRESS
        
        await self.db.commit()
        await self.db.refresh(response)
        
        # Notify relevant party
        if self.notification_manager and ticket:
            if is_internal:
                # Notify assigned admin
                if ticket.assigned_to:
                    await self.notification_manager.notify_user(
                        ticket.assigned_to,
                        f"Internal note on: {ticket.title}",
                        "A new internal note was added"
                    )
            else:
                # Notify ticket owner if admin responded
                responding_user = await self.db.get(Ticket, user_id)
                if responding_user and responding_user.id != ticket.user_id:
                    await self.notification_manager.notify_user(
                        ticket.user_id,
                        f"New response on: {ticket.title}",
                        "An admin has responded to your ticket"
                    )
        
        return response
    
    async def get_ticket_responses(
        self,
        ticket_id: str,
        include_internal: bool = False
    ) -> List[TicketResponse]:
        """Get all responses for a ticket."""
        query = select(TicketResponse).where(TicketResponse.ticket_id == ticket_id)
        
        if not include_internal:
            query = query.where(TicketResponse.is_internal == "N")
        
        query = query.order_by(asc(TicketResponse.created_at))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    # ==================== Statistics ====================
    
    async def get_ticket_stats(self) -> dict:
        """Get ticket statistics for admin dashboard."""
        # Count by status
        status_counts = {}
        for status in TicketStatus:
            result = await self.db.execute(
                select(Ticket).where(Ticket.status == status)
            )
            status_counts[status.value] = len(result.scalars().all())
        
        # Count by priority
        priority_counts = {}
        for priority in TicketPriority:
            result = await self.db.execute(
                select(Ticket).where(Ticket.priority == priority)
            )
            priority_counts[priority.value] = len(result.scalars().all())
        
        # Open tickets count
        open_result = await self.db.execute(
            select(Ticket).where(Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS]))
        )
        
        # Unassigned open tickets
        unassigned_result = await self.db.execute(
            select(Ticket).where(
                Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS]),
                Ticket.assigned_to.is_(None)
            )
        )
        
        return {
            "total": sum(status_counts.values()),
            "by_status": status_counts,
            "by_priority": priority_counts,
            "open": len(open_result.scalars().all()),
            "unassigned": len(unassigned_result.scalars().all())
        }
    
    # ==================== Quick Actions ====================
    
    async def is_challenge_broken(self, challenge_id: str) -> List[Ticket]:
        """Check if users are reporting a challenge as broken."""
        result = await self.db.execute(
            select(Ticket).where(
                Ticket.challenge_id == challenge_id,
                Ticket.category == TicketCategory.CHALLENGE_ISSUE,
                Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS])
            )
        )
        return result.scalars().all()
    
    async def close_resolved_tickets(self, days_old: int = 7) -> int:
        """Auto-close tickets that have been resolved for X days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        result = await self.db.execute(
            select(Ticket).where(
                Ticket.status == TicketStatus.RESOLVED,
                Ticket.resolved_at < cutoff_date
            )
        )
        tickets = result.scalars().all()
        
        for ticket in tickets:
            ticket.status = TicketStatus.CLOSED
            ticket.closed_at = datetime.utcnow()
        
        await self.db.commit()
        return len(tickets)
