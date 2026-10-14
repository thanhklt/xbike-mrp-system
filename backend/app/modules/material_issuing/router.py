"""Persisted material issuing endpoints. Demo data lives only in seed.sql."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_payload, require_roles
from app.modules.material_issuing.models import MaterialIssueItem, MaterialIssueRequest
from app.modules.material_issuing.schemas import (
    MaterialIssueRequestCreate,
    MaterialIssueRequestResponse,
)
from app.shared.database_queries import create_record, get_record, list_records
from app.shared.pagination import PageParams, PaginatedResponse, get_pagination_params

router = APIRouter(
    prefix="/material-issuing",
    tags=["Material Issuing"],
    dependencies=[Depends(get_current_user_payload)],
)


@router.get("", response_model=PaginatedResponse[MaterialIssueRequestResponse])
async def list_entries(
    params: Annotated[PageParams, Depends(get_pagination_params)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await list_records(
        db,
        MaterialIssueRequest,
        MaterialIssueRequestResponse,
        params,
        MaterialIssueRequest.loai_phieu == "xuat_vat_tu",
    )


@router.get("/{issue_id}", response_model=MaterialIssueRequestResponse)
async def get_entry(issue_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    return await get_record(
        db, MaterialIssueRequest, issue_id, MaterialIssueRequest.loai_phieu == "xuat_vat_tu"
    )


@router.post("", response_model=MaterialIssueRequestResponse, status_code=201)
async def create_entry(
    payload: MaterialIssueRequestCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly", "nhan_vien"]))],
):
    if payload.loai_phieu != "xuat_vat_tu":
        raise HTTPException(status_code=422, detail="Incorrect issue type for this endpoint")
    return await create_record(
        db,
        MaterialIssueRequest,
        payload,
        actor,
        "phieu_xuat",
        child=(MaterialIssueItem, "phieu_xuat_id"),
    )
