"""
Ticket API Routes - User and Admin endpoints for support tickets.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.dependencies import get_db, get_current_user, require_admin
from app.models.ticket import TicketStatus, TicketPriority, TicketCategory
from app.models.user import User
from app.services.ticket_service import TicketService

router = APIRouter(prefix="/tickets", tags=["Tickets"])


# ==================== Pydantic Schemas ====================

class TicketCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=10)
    category: TicketCategory = TicketCategory.QUESTION
    priority: TicketPriority = TicketPriority.MEDIUM
    challenge_id: Optional[str] = None


class TicketResponseCreate(BaseModel):
    content: str = Field(..., min_length=1)
    is_internal: bool = False


class TicketUpdate(BaseModel):
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    assigned_to: Optional[str] = None


class TicketResponseOut(BaseModel):
    id: str
    content: str
    is_internal: bool
    created_at: str
    user: dict
    
    class Config:
        from_attributes = True


class TicketOut(BaseModel):
    id: str
    title: str
    description: str
    category: str
    status: str
    priority: str
    challenge_id: Optional[str]
    assigned_to: Optional[str]
    created_at: str
    updated_at: str
    user: dict
    assignee: Optional[dict] = None
    responses: List[TicketResponseOut] = []
    
    class Config:
        from_attributes = True


class TicketListOut(BaseModel):
    id: str
    title: str
    category: str
    status: str
    priority: str
    created_at: str
    user: dict
    
    class Config:
        from_attributes = True


class TicketStats(BaseModel):
    total: int
    by_status: dict
    by_priority: dict
    open: int
    unassigned: int


# ==================== User Routes ====================

@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    data: TicketCreate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new support ticket."""
    service = TicketService(db)
    ticket = await service.create_ticket(
        user_id=current_user.id,
        title=data.title,
        description=data.description,
        category=data.category,
        priority=data.priority,
        challenge_id=data.challenge_id
    )
    return ticket


@router.get("/my", response_model=List[TicketListOut])
async def get_my_tickets(
    status: Optional[TicketStatus] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's tickets."""
    service = TicketService(db)
    tickets = await service.get_user_tickets(
        user_id=current_user.id,
        status=status,
        limit=limit,
        offset=offset
    )
    return tickets


@router.get("/my/{ticket_id}", response_model=TicketOut)
async def get_my_ticket(
    ticket_id: str,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific ticket (must be owned by user)."""
    service = TicketService(db)
    ticket = await service.get_ticket(ticket_id)
    
    if not ticket or ticket.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return ticket


@router.post("/my/{ticket_id}/respond", response_model=TicketResponseOut)
async def respond_to_ticket(
    ticket_id: str,
    data: TicketResponseCreate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a response to user's ticket."""
    service = TicketService(db)
    
    # Verify ticket ownership
    ticket = await service.get_ticket(ticket_id)
    if not ticket or ticket.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Users cannot create internal notes
    if data.is_internal:
        raise HTTPException(status_code=403, detail="Cannot create internal notes")
    
    response = await service.add_response(
        ticket_id=ticket_id,
        user_id=current_user.id,
        content=data.content,
        is_internal=False
    )
    return response


# ==================== Admin Routes ====================

@router.get("/admin/all", response_model=List[TicketListOut])
async def get_all_tickets(
    status: Optional[TicketStatus] = None,
    priority: Optional[TicketPriority] = None,
    assigned_to: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
    _: User = Depends(require_admin)
):
    """Get all tickets (admin only)."""
    service = TicketService(db)
    tickets = await service.get_all_tickets(
        status=status,
        priority=priority,
        assigned_to=assigned_to,
        limit=limit,
        offset=offset
    )
    return tickets


@router.get("/admin/{ticket_id}", response_model=TicketOut)
async def get_ticket_admin(
    ticket_id: str,
    db=Depends(get_db),
    _: User = Depends(require_admin)
):
    """Get any ticket with internal notes (admin only)."""
    service = TicketService(db)
    ticket = await service.get_ticket(ticket_id)
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return ticket


@router.patch("/admin/{ticket_id}", response_model=TicketOut)
async def update_ticket_admin(
    ticket_id: str,
    data: TicketUpdate,
    db=Depends(get_db),
    _: User = Depends(require_admin)
):
    """Update ticket status/priority/assignment (admin only)."""
    service = TicketService(db)
    ticket = await service.update_ticket(
        ticket_id=ticket_id,
        status=data.status,
        priority=data.priority,
        assigned_to=data.assigned_to
    )
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return ticket


@router.post("/admin/{ticket_id}/respond", response_model=TicketResponseOut)
async def respond_to_ticket_admin(
    ticket_id: str,
    data: TicketResponseCreate,
    db=Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Add response to ticket (admin only, can be internal)."""
    service = TicketService(db)
    
    ticket = await service.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    response = await service.add_response(
        ticket_id=ticket_id,
        user_id=current_user.id,
        content=data.content,
        is_internal=data.is_internal
    )
    return response


@router.get("/admin/stats/summary", response_model=TicketStats)
async def get_ticket_stats(
    db=Depends(get_db),
    _: User = Depends(require_admin)
):
    """Get ticket statistics (admin only)."""
    service = TicketService(db)
    stats = await service.get_ticket_stats()
    return stats


@router.get("/admin/challenge/{challenge_id}/issues")
async def get_challenge_issues(
    challenge_id: str,
    db=Depends(get_db),
    _: User = Depends(require_admin)
):
    """Get all open issues for a specific challenge."""
    service = TicketService(db)
    tickets = await service.is_challenge_broken(challenge_id)
    return {
        "challenge_id": challenge_id,
        "open_issues": len(tickets),
        "tickets": tickets
    }
