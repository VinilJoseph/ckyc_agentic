"""Unit tests for SQLAlchemy models, TenantMixin isolation, and schema relationships."""
import uuid
from sqlalchemy.orm import configure_mappers
from sqlalchemy import inspect

from app.models.base import Base, GUID, TenantMixin, TimestampMixin
from app.models.tenant import Tenant, Subscription, UsageRecord
from app.models.case import KycCase
from app.models.applicant import Applicant, BusinessRepresentative
from app.models.document import CaseDocument
from app.models.field import ExtractedField
from app.models.share import ShareGrant
from app.models.audit import AuditEvent
from app.models.email import MailIngestionRecord
from app.models.user import User, TenantMembership


def test_configure_mappers_succeeds():
    """Verify that configure_mappers() completes cleanly without NoForeignKeysError."""
    # This ensures all relationships (Tenant.cases, KycCase.tenant, etc.) have valid FK joins
    configure_mappers()


def test_tenant_mixin_foreign_key():
    """Verify that TenantMixin defines a foreign key pointing to tenants.id with CASCADE delete."""
    mapper = inspect(KycCase)
    tenant_id_col = mapper.columns["tenant_id"]
    
    assert len(tenant_id_col.foreign_keys) == 1
    fk = list(tenant_id_col.foreign_keys)[0]
    assert fk.target_fullname == "tenants.id"
    assert fk.ondelete.upper() == "CASCADE"


def test_tenant_relationships_configuration():
    """Verify bidirectional relationships between Tenant and dependent entities."""
    tenant_mapper = inspect(Tenant)
    assert "cases" in tenant_mapper.relationships
    assert "subscriptions" in tenant_mapper.relationships
    assert "usage_records" in tenant_mapper.relationships
    assert "memberships" in tenant_mapper.relationships

    case_rel = tenant_mapper.relationships["cases"]
    assert case_rel.back_populates == "cases" or case_rel.argument == "KycCase"

    kyc_case_mapper = inspect(KycCase)
    assert "tenant" in kyc_case_mapper.relationships
    assert kyc_case_mapper.relationships["tenant"].argument == "Tenant"


def test_guid_type_decorator():
    """Verify GUID TypeDecorator handles UUID objects, string UUIDs, and deterministic strings."""
    guid_type = GUID()
    
    # 1. None
    assert guid_type.process_bind_param(None, None) is None
    assert guid_type.process_result_value(None, None) is None
    
    # 2. uuid.UUID instance
    u = uuid.uuid4()
    assert guid_type.process_bind_param(u, None) == str(u)
    assert guid_type.process_result_value(str(u), None) == u
    
    # 3. Valid UUID string
    u_str = str(u)
    assert guid_type.process_bind_param(u_str, None) == u_str
    
    # 4. Non-hex arbitrary test string (deterministic uuid5 DNS fallback)
    custom_str = "tenant-alpha-001"
    bound = guid_type.process_bind_param(custom_str, None)
    expected_uuid5 = str(uuid.uuid5(uuid.NAMESPACE_DNS, custom_str))
    assert bound == expected_uuid5
    assert guid_type.process_result_value(custom_str, None) == uuid.UUID(expected_uuid5)


def test_model_instantiation():
    """Verify creating model instances with appropriate attributes."""
    t_id = uuid.uuid4()
    tenant = Tenant(
        id=t_id,
        name="FinTech Corp",
        slug="fintech-corp",
        plan="growth",
        status="active"
    )
    assert tenant.id == t_id
    assert tenant.slug == "fintech-corp"

    app_id = uuid.uuid4()
    applicant = Applicant(
        id=app_id,
        tenant_id=t_id,
        applicant_type="individual",
        first_name="Rohan",
        last_name="Sharma",
        email="rohan@example.com"
    )
    assert applicant.tenant_id == t_id
    assert applicant.first_name == "Rohan"

    case_id = uuid.uuid4()
    case = KycCase(
        id=case_id,
        tenant_id=t_id,
        applicant_id=app_id,
        case_number="CASE-1001",
        purpose="Account Opening",
        case_type="individual",
        status="draft"
    )
    assert case.case_number == "CASE-1001"
    assert case.status == "draft"
    assert case.tenant_id == t_id
