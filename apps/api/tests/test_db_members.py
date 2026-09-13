from unittest.mock import MagicMock, patch
from uuid import uuid4

import psycopg
import pytest

from app.api.v1.schemas import OrganizationMemberCreate, OrganizationRole
from app.core.exceptions import (
    DuplicateSlugError,
    LastAdminError,
    MemberAlreadyExistsError,
    OrganizationNotFoundError,
)
from app.infrastructure.database.organization_members import (
    add_organization_member,
    delete_organization_member,
    update_organization_member,
)
from app.infrastructure.database.organizations import create_organization


class _MockContextManager:
    def __init__(self, obj):
        self.obj = obj

    def __enter__(self):
        return self.obj

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def test_db_delete_last_admin_raises_error():
    org_id = uuid4()
    user_id = uuid4()

    mock_cursor = MagicMock()
    # 1st fetchone: org exists (id,)
    # 2nd fetchone: member exists with role ('ADMIN',)
    # 3rd fetchone: admin count (1,)
    mock_cursor.fetchone.side_effect = [
        (org_id,),
        ("ADMIN",),
        (1,),
    ]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = _MockContextManager(mock_cursor)

    with patch("psycopg.connect", return_value=_MockContextManager(mock_conn)):
        with pytest.raises(LastAdminError, match="at least one admin"):
            delete_organization_member(org_id, user_id)


def test_db_delete_admin_when_multiple_admins_exist():
    org_id = uuid4()
    user_id = uuid4()

    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = [
        (org_id,),
        ("ADMIN",),
        (2,),  # 2 admins exist
    ]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = _MockContextManager(mock_cursor)

    with patch("psycopg.connect", return_value=_MockContextManager(mock_conn)):
        result = delete_organization_member(org_id, user_id)
        assert result is True
        # Verify DELETE was called
        delete_calls = [
            call for call in mock_cursor.execute.call_args_list
            if "DELETE FROM organization_members" in call[0][0]
        ]
        assert len(delete_calls) == 1


def test_db_delete_non_admin_member():
    org_id = uuid4()
    user_id = uuid4()

    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = [
        (org_id,),
        ("OPERATOR",),
    ]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = _MockContextManager(mock_cursor)

    with patch("psycopg.connect", return_value=_MockContextManager(mock_conn)):
        result = delete_organization_member(org_id, user_id)
        assert result is True


def test_db_demote_last_admin_raises_error():
    org_id = uuid4()
    user_id = uuid4()

    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = [
        (org_id,),
        ("ADMIN",),
        (1,),  # only 1 admin
    ]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = _MockContextManager(mock_cursor)

    with patch("psycopg.connect", return_value=_MockContextManager(mock_conn)):
        with pytest.raises(LastAdminError, match="at least one admin"):
            update_organization_member(org_id, user_id, OrganizationRole.OPERATOR)


def test_db_demote_admin_when_multiple_admins_exist():
    org_id = uuid4()
    user_id = uuid4()

    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = [
        (org_id,),
        ("ADMIN",),
        (2,),  # 2 admins
        (org_id, user_id, "OPERATOR"),  # updated row
    ]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = _MockContextManager(mock_cursor)

    with patch("psycopg.connect", return_value=_MockContextManager(mock_conn)):
        member = update_organization_member(org_id, user_id, OrganizationRole.OPERATOR)
        assert member is not None
        assert member.role == "OPERATOR"


def test_db_add_member_duplicate_raises_error():
    org_id = uuid4()
    user_id = uuid4()

    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = [
        (org_id,),  # org exists
        (user_id,),  # user exists
    ]
    # INSERT raises UniqueViolation
    mock_cursor.execute.side_effect = [
        None,  # SELECT org
        None,  # SELECT user
        psycopg.errors.UniqueViolation("duplicate key"),  # INSERT
    ]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = _MockContextManager(mock_cursor)

    with patch("psycopg.connect", return_value=_MockContextManager(mock_conn)):
        with pytest.raises(MemberAlreadyExistsError):
            add_organization_member(
                org_id,
                OrganizationMemberCreate(user_id=user_id, role=OrganizationRole.VIEWER),
            )
