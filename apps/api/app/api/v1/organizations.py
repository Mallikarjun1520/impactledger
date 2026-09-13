from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.schemas import (
    OrganizationCreate,
    OrganizationMemberCreate,
    OrganizationMemberUpdate,
)
from app.core.auth import get_current_user
from app.core.authorization import get_current_membership
from app.core.exceptions import (
    DuplicateSlugError,
    LastAdminError,
    MemberAlreadyExistsError,
    OrganizationNotFoundError,
)
from app.infrastructure.database.organization_members import (
    OrganizationMembership,
    add_organization_member,
    delete_organization_member,
    list_organization_members,
    update_organization_member,
)
from app.infrastructure.database.organizations import (
    create_organization,
    get_organization,
)

router = APIRouter()


@router.post("/organizations")
def create_organization_endpoint(
    data: OrganizationCreate,
    user_id: UUID = Depends(get_current_user),
) -> dict:
    try:
        organization = create_organization(
            data=data,
            user_id=user_id,
        )

        return {
            "id": str(organization["id"]),
            "name": organization["name"],
            "slug": organization["slug"],
            "description": organization["description"],
        }

    except DuplicateSlugError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@router.get("/organizations/{organization_id}")
def get_organization_endpoint(
    organization_id: UUID,
    membership: OrganizationMembership = Depends(get_current_membership),
) -> dict:
    if membership.organization_id != organization_id:
        raise HTTPException(
            status_code=403,
            detail="Organization ID does not match X-Organization-ID",
        )

    organization = get_organization(organization_id)

    if organization is None:
        raise HTTPException(
            status_code=404,
            detail="Organization not found",
        )

    return {
        "id": str(organization["id"]),
        "name": organization["name"],
        "slug": organization["slug"],
        "description": organization["description"],
        "created_at": organization["created_at"].isoformat(),
        "updated_at": organization["updated_at"].isoformat(),
    }


@router.get("/organizations/{organization_id}/members")
def list_members_endpoint(
    organization_id: UUID,
    membership: OrganizationMembership = Depends(get_current_membership),
) -> list[dict]:
    if membership.organization_id != organization_id:
        raise HTTPException(
            status_code=403,
            detail="Organization ID does not match X-Organization-ID",
        )

    members = list_organization_members(organization_id)

    return [
        {
            "organization_id": str(member.organization_id),
            "user_id": str(member.user_id),
            "role": member.role,
        }
        for member in members
    ]


@router.post("/organizations/{organization_id}/members")
def add_member_endpoint(
    organization_id: UUID,
    data: OrganizationMemberCreate,
    membership: OrganizationMembership = Depends(get_current_membership),
) -> dict:
    if membership.role != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Only organization admins can manage members",
        )

    if membership.organization_id != organization_id:
        raise HTTPException(
            status_code=403,
            detail="Organization ID does not match X-Organization-ID",
        )

    try:
        member = add_organization_member(
            organization_id=organization_id,
            data=data,
        )

        return {
            "organization_id": str(member.organization_id),
            "user_id": str(member.user_id),
            "role": member.role,
        }

    except MemberAlreadyExistsError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        )

    except OrganizationNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@router.patch("/organizations/{organization_id}/members/{user_id}")
def update_member_endpoint(
    organization_id: UUID,
    user_id: UUID,
    data: OrganizationMemberUpdate,
    membership: OrganizationMembership = Depends(get_current_membership),
) -> dict:
    if membership.role != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Only organization admins can manage members",
        )

    if membership.organization_id != organization_id:
        raise HTTPException(
            status_code=403,
            detail="Organization ID does not match X-Organization-ID",
        )

    try:
        member = update_organization_member(
            organization_id=organization_id,
            user_id=user_id,
            role=data.role,
        )
    except LastAdminError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        )

    if member is None:
        raise HTTPException(
            status_code=404,
            detail="Organization member not found",
        )

    return {
        "organization_id": str(member.organization_id),
        "user_id": str(member.user_id),
        "role": member.role,
    }


@router.delete("/organizations/{organization_id}/members/{user_id}")
def delete_member_endpoint(
    organization_id: UUID,
    user_id: UUID,
    membership: OrganizationMembership = Depends(get_current_membership),
) -> dict:
    if membership.role != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Only organization admins can manage members",
        )

    if membership.organization_id != organization_id:
        raise HTTPException(
            status_code=403,
            detail="Organization ID does not match X-Organization-ID",
        )

    try:
        deleted = delete_organization_member(
            organization_id=organization_id,
            user_id=user_id,
        )
    except LastAdminError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Organization member not found",
        )

    return {
        "status": "member removed",
        "organization_id": str(organization_id),
        "user_id": str(user_id),
    }