"""Email Intake & Exception Queue Service.

Implements:
- Hierarchical case matching engine:
  1. Primary: [CASE-XXXX] subject regex token matching KycCase.case_number
  2. Secondary fallback: Sender email matching Applicant.email with exactly 1 active case
- Idempotency guard via unique Message-ID with cross-tenant metadata sanitization
- Case document ingestion, magic byte verification, and disk storage
- State machine transition to documents_received
- Genuine background OCR extraction and KYC validation execution
- Email exception queue persistence and triage actions (manual assignment and dismissal)
"""
from datetime import datetime, timezone
import email.utils
import hashlib
import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple, Union
import uuid

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.context import tenant_context
from app.core.database import async_session_maker
from app.core.state_machine import CaseStatus, transition_case
from app.models.applicant import Applicant
from app.models.audit import AuditEvent
from app.models.case import KycCase
from app.models.document import CaseDocument
from app.models.email import MailIngestionRecord
from app.models.field import ExtractedField
from app.models.tenant import UsageRecord
from app.services.email.parser import ParsedAttachmentDTO, ParsedEmailDTO
from app.services.ocr.tier_manager import ocr_engine
from app.services.storage.local import LocalStorageService, detect_magic_mime, storage_service
from app.services.validation.engine import validation_engine

logger = logging.getLogger(__name__)


class EmailIntakeService:
    def __init__(
        self,
        storage: Optional[LocalStorageService] = None,
        session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
    ):
        self.storage = storage or storage_service
        self.session_factory = session_factory

    async def find_matching_case(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        case_number_ref: Optional[str],
        sender_email: str,
    ) -> Optional[KycCase]:
        """Hierarchical case matching:
        1. Primary: If case_number_ref is present, match active case with that case_number in tenant.
        2. Secondary: If no case_number_ref (or not found), look up applicant by sender email having
           exactly ONE active non-terminal case in tenant.
        """
        # Primary: Subject case_number token
        if case_number_ref:
            stmt = select(KycCase).where(
                KycCase.tenant_id == tenant_id,
                func.upper(KycCase.case_number) == case_number_ref.upper(),
                KycCase.status.not_in(["closed", "approved", "rejected"]),
            )
            res = (await db.execute(stmt)).scalar_one_or_none()
            if res:
                return res
            # Explicit case token specified but not found in tenant: do not guess or fall back
            return None

        # Secondary Fallback: Sender email lookup
        clean_sender = email.utils.parseaddr(sender_email)[1].lower() if sender_email else ""
        if clean_sender and "@" in clean_sender:
            stmt = (
                select(KycCase)
                .join(Applicant, KycCase.applicant_id == Applicant.id)
                .where(
                    KycCase.tenant_id == tenant_id,
                    func.lower(Applicant.email) == clean_sender,
                    KycCase.status.not_in(["closed", "approved", "rejected"]),
                )
            )
            active_cases = (await db.execute(stmt)).scalars().all()
            if len(active_cases) == 1:
                return active_cases[0]

        return None

    async def ingest_parsed_email(
        self,
        db: AsyncSession,
        parsed: ParsedEmailDTO,
        tenant_id: uuid.UUID,
        background_tasks: Optional[BackgroundTasks] = None,
        raw_eml_bytes: Optional[bytes] = None,
    ) -> Tuple[str, MailIngestionRecord, Optional[KycCase]]:
        """Processes a parsed email:
        - Idempotency check via message_id with cross-tenant leak prevention
        - Hierarchical matching to active case or routing to exception queue
        - File storage, document persistence, and case state transition
        """
        # 1. Idempotency Check with Cross-Tenant Isolation
        stmt_dup = (
            select(MailIngestionRecord)
            .where(MailIngestionRecord.message_id == parsed.message_id)
            .execution_options(bypass_tenant_isolation=True)
        )
        existing = (await db.execute(stmt_dup)).scalar_one_or_none()
        if existing:
            target_case = None
            if existing.tenant_id == tenant_id:
                # Same tenant: safely fetch target case
                if existing.case_id:
                    stmt_case = select(KycCase).where(
                        KycCase.id == existing.case_id,
                        KycCase.tenant_id == tenant_id,
                    )
                    target_case = (await db.execute(stmt_case)).scalar_one_or_none()
                return "idempotent_duplicate", existing, target_case
            else:
                # Foreign tenant duplicate: sanitize record to prevent cross-tenant metadata disclosure
                sanitized_rec = MailIngestionRecord(
                    id=existing.id,
                    tenant_id=tenant_id,
                    message_id=existing.message_id,
                    sender=existing.sender,
                    recipient=existing.recipient,
                    subject=existing.subject,
                    body_text=existing.body_text,
                    status=existing.status,
                    case_id=None,
                    attachment_count=existing.attachment_count,
                    raw_payload_storage_key=None,
                    error_message=existing.error_message,
                    received_at=existing.received_at,
                )
                return "idempotent_duplicate", sanitized_rec, None

        # 2. Case Matching
        target_case = await self.find_matching_case(
            db, tenant_id, parsed.case_number_ref, parsed.sender
        )

        if target_case:
            # Matched Route
            rec = MailIngestionRecord(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                message_id=parsed.message_id,
                sender=parsed.sender,
                recipient=parsed.recipient or "kyc-intake@fintechbank.com",
                subject=parsed.subject,
                body_text=parsed.body_text,
                status="attached_to_case",
                case_id=target_case.id,
                attachment_count=parsed.attachment_count,
            )
            db.add(rec)
            await db.flush()

            # Attach documents
            created_docs = await self._attach_attachments_to_case(
                db, target_case, parsed.attachments, tenant_id
            )

            # Advance state machine to DOCUMENTS_RECEIVED
            if target_case.status in (
                CaseStatus.DRAFT.value,
                CaseStatus.AWAITING_DOCUMENTS.value,
                CaseStatus.INVITATION_SENT.value,
            ):
                await transition_case(target_case, CaseStatus.DOCUMENTS_RECEIVED, db=db)

            # Enqueue background OCR and validation pipeline
            if background_tasks and created_docs:
                bound_factory = None
                if db.bind:
                    bound_factory = async_sessionmaker(
                        db.bind,
                        class_=AsyncSession,
                        expire_on_commit=False,
                        autocommit=False,
                        autoflush=False,
                    )
                background_tasks.add_task(
                    self.run_background_pipeline,
                    case_id=target_case.id,
                    tenant_id=tenant_id,
                    doc_ids=[d.id for d in created_docs],
                    session_factory=bound_factory,
                )

            # Emit Audit Event
            audit = AuditEvent(
                tenant_id=tenant_id,
                action="email_intake_attached",
                resource_type="case",
                resource_id=target_case.id,
                metadata_={
                    "message_id": parsed.message_id,
                    "attachments_count": parsed.attachment_count,
                    "case_number": target_case.case_number,
                },
            )
            db.add(audit)

            # Increment usage record
            stmt_usage = select(UsageRecord).where(
                UsageRecord.tenant_id == tenant_id,
                UsageRecord.metric_name == "documents_uploaded",
            )
            usage = (await db.execute(stmt_usage)).scalar_one_or_none()
            if usage:
                usage.metric_value += parsed.attachment_count
            else:
                db.add(
                    UsageRecord(
                        id=uuid.uuid4(),
                        tenant_id=tenant_id,
                        metric_name="documents_uploaded",
                        metric_value=parsed.attachment_count,
                    )
                )

            await db.commit()
            await db.refresh(rec)
            await db.refresh(target_case)
            return "attached_to_case", rec, target_case

        else:
            # Unmatched Route -> Exception Queue
            exc_id = uuid.uuid4()
            raw_key: Optional[str] = None

            # Persist raw payload / attachments in unmatched directory
            if raw_eml_bytes:
                raw_key = await self.storage.save_unmatched_file(
                    tenant_id=tenant_id,
                    exception_id=exc_id,
                    filename="submission.eml",
                    file_bytes=raw_eml_bytes,
                )

            for att in parsed.attachments:
                att_key = await self.storage.save_unmatched_file(
                    tenant_id=tenant_id,
                    exception_id=exc_id,
                    filename=att.filename,
                    file_bytes=att.data,
                )
                if not raw_key:
                    raw_key = att_key

            rec = MailIngestionRecord(
                id=exc_id,
                tenant_id=tenant_id,
                message_id=parsed.message_id,
                sender=parsed.sender,
                recipient=parsed.recipient or "kyc-intake@fintechbank.com",
                subject=parsed.subject,
                body_text=parsed.body_text,
                status="unmatched",
                case_id=None,
                attachment_count=parsed.attachment_count,
                raw_payload_storage_key=raw_key,
                error_message="Unmatched case reference routed to exception queue",
            )
            db.add(rec)
            await db.flush()

            # Emit Audit Event
            audit = AuditEvent(
                tenant_id=tenant_id,
                action="email_exception_queued",
                resource_type="email_exception",
                resource_id=rec.id,
                metadata_={
                    "message_id": parsed.message_id,
                    "sender": parsed.sender,
                    "subject": parsed.subject,
                },
            )
            db.add(audit)

            await db.commit()
            await db.refresh(rec)
            return "routed_to_exception_queue", rec, None

    async def _attach_attachments_to_case(
        self,
        db: AsyncSession,
        case: KycCase,
        attachments: List[ParsedAttachmentDTO],
        tenant_id: uuid.UUID,
    ) -> List[CaseDocument]:
        """Saves decoded attachment bytes to disk and registers CaseDocument records."""
        docs: List[CaseDocument] = []
        for att in attachments:
            doc_id = uuid.uuid4()
            try:
                mime = detect_magic_mime(att.data)
            except Exception:
                mime = att.content_type or "application/octet-stream"

            storage_key = await self.storage.save_file(
                tenant_id=tenant_id,
                case_id=case.id,
                doc_id=doc_id,
                filename=att.filename,
                file_bytes=att.data,
            )

            # Auto-detect document type from filename or default to identity_card
            fn_lower = att.filename.lower()
            if "aadhaar" in fn_lower:
                doc_type = "aadhaar"
            elif "pan" in fn_lower:
                doc_type = "pan"
            elif "passport" in fn_lower:
                doc_type = "passport"
            elif "dl" in fn_lower or "driving" in fn_lower:
                doc_type = "driving_licence"
            else:
                doc_type = "identity_card"

            doc = CaseDocument(
                id=doc_id,
                tenant_id=tenant_id,
                case_id=case.id,
                document_type=doc_type,
                storage_key=storage_key,
                original_filename=att.filename,
                file_hash=att.sha256_hash,
                mime_type=mime,
                file_size=att.size,
                source="email",
                review_status="pending",
            )
            db.add(doc)
            docs.append(doc)

        await db.flush()
        return docs

    async def assign_exception_to_case(
        self,
        db: AsyncSession,
        exception_id: uuid.UUID,
        target_case_id: uuid.UUID,
        tenant_id: uuid.UUID,
        reviewer_id: Optional[uuid.UUID] = None,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> Tuple[MailIngestionRecord, KycCase]:
        """Manually assigns an unmatched email exception to a target KYC case."""
        # 1. Fetch exception with strict tenant scoping
        stmt_exc = select(MailIngestionRecord).where(
            MailIngestionRecord.id == exception_id,
            MailIngestionRecord.tenant_id == tenant_id,
        )
        exc = (await db.execute(stmt_exc)).scalar_one_or_none()
        if not exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email exception not found",
            )

        # 2. Check if eligible for assignment (strictly unmatched status)
        if exc.status != "unmatched":
            if exc.status in ("assigned", "matched"):
                detail_msg = "Email exception is already assigned"
            else:
                detail_msg = f"Cannot assign email exception in '{exc.status}' status"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail_msg,
            )

        # 3. Fetch target case with strict tenant scoping
        stmt_case = select(KycCase).where(
            KycCase.id == target_case_id,
            KycCase.tenant_id == tenant_id,
        )
        target_case = (await db.execute(stmt_case)).scalar_one_or_none()
        if not target_case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target case not found",
            )

        # 4. Check terminal case status
        if target_case.status in ("closed", "approved", "rejected"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot assign email exception to terminal case in '{target_case.status}' status",
            )

        # 5. Transfer attachments from unmatched storage to target case directory
        unmatched_dir = (
            self.storage.base_dir / "tenants" / str(tenant_id) / "unmatched" / str(exc.id)
        )
        assigned_docs: List[CaseDocument] = []
        if unmatched_dir.exists() and unmatched_dir.is_dir():
            for fpath in unmatched_dir.iterdir():
                if (
                    fpath.is_file()
                    and not fpath.name.endswith(".json")
                    and fpath.name != "submission.eml"
                ):
                    file_bytes = fpath.read_bytes()
                    doc_id = uuid.uuid4()
                    try:
                        mime = detect_magic_mime(file_bytes)
                    except Exception:
                        mime = "application/octet-stream"

                    file_hash = hashlib.sha256(file_bytes).hexdigest()
                    storage_key = await self.storage.save_file(
                        tenant_id=tenant_id,
                        case_id=target_case.id,
                        doc_id=doc_id,
                        filename=fpath.name,
                        file_bytes=file_bytes,
                    )
                    fn_lower = fpath.name.lower()
                    if "aadhaar" in fn_lower:
                        doc_type = "aadhaar"
                    elif "pan" in fn_lower:
                        doc_type = "pan"
                    elif "passport" in fn_lower:
                        doc_type = "passport"
                    elif "dl" in fn_lower or "driving" in fn_lower:
                        doc_type = "driving_licence"
                    else:
                        doc_type = "identity_card"

                    doc = CaseDocument(
                        id=doc_id,
                        tenant_id=tenant_id,
                        case_id=target_case.id,
                        document_type=doc_type,
                        storage_key=storage_key,
                        original_filename=fpath.name,
                        file_hash=file_hash,
                        mime_type=mime,
                        file_size=len(file_bytes),
                        source="email",
                        review_status="pending",
                    )
                    db.add(doc)
                    assigned_docs.append(doc)

        # 6. Advance case status to DOCUMENTS_RECEIVED
        if target_case.status in (
            CaseStatus.DRAFT.value,
            CaseStatus.AWAITING_DOCUMENTS.value,
            CaseStatus.INVITATION_SENT.value,
        ):
            await transition_case(target_case, CaseStatus.DOCUMENTS_RECEIVED, db=db)

        # 7. Update exception record status
        exc.status = "assigned"
        exc.case_id = target_case.id

        # 8. Increment tenant usage counter for manually assigned documents
        if assigned_docs:
            stmt_usage = select(UsageRecord).where(
                UsageRecord.tenant_id == tenant_id,
                UsageRecord.metric_name == "documents_uploaded",
            )
            usage = (await db.execute(stmt_usage)).scalar_one_or_none()
            if usage:
                usage.metric_value += len(assigned_docs)
            else:
                db.add(
                    UsageRecord(
                        id=uuid.uuid4(),
                        tenant_id=tenant_id,
                        metric_name="documents_uploaded",
                        metric_value=len(assigned_docs),
                    )
                )

        # 9. Enqueue background OCR and validation pipeline if requested
        if background_tasks and assigned_docs:
            bound_factory = None
            if db.bind:
                bound_factory = async_sessionmaker(
                    db.bind,
                    class_=AsyncSession,
                    expire_on_commit=False,
                    autocommit=False,
                    autoflush=False,
                )
            background_tasks.add_task(
                self.run_background_pipeline,
                case_id=target_case.id,
                tenant_id=tenant_id,
                doc_ids=[d.id for d in assigned_docs],
                session_factory=bound_factory,
            )

        # 10. Audit logging
        audit = AuditEvent(
            tenant_id=tenant_id,
            actor_id=reviewer_id,
            action="email_exception_assigned",
            resource_type="email_exception",
            resource_id=exc.id,
            metadata_={
                "assigned_case_id": str(target_case.id),
                "case_number": target_case.case_number,
                "documents_assigned": len(assigned_docs),
            },
        )
        db.add(audit)

        await db.commit()
        await db.refresh(exc)
        await db.refresh(target_case)
        return exc, target_case

    async def dismiss_exception(
        self,
        db: AsyncSession,
        exception_id: uuid.UUID,
        tenant_id: uuid.UUID,
        reviewer_id: Optional[uuid.UUID] = None,
    ) -> MailIngestionRecord:
        """Dismisses an unwanted or spam email exception from the triage queue."""
        stmt = select(MailIngestionRecord).where(
            MailIngestionRecord.id == exception_id,
            MailIngestionRecord.tenant_id == tenant_id,
        )
        exc = (await db.execute(stmt)).scalar_one_or_none()
        if not exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email exception not found",
            )

        exc.status = "dismissed"

        audit = AuditEvent(
            tenant_id=tenant_id,
            actor_id=reviewer_id,
            action="email_exception_dismissed",
            resource_type="email_exception",
            resource_id=exc.id,
            metadata_={"status": "dismissed"},
        )
        db.add(audit)

        await db.commit()
        await db.refresh(exc)
        return exc

    async def run_background_pipeline(
        self,
        case_id: uuid.UUID,
        tenant_id: uuid.UUID,
        doc_ids: List[uuid.UUID],
        session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
    ) -> None:
        """Asynchronous document OCR extraction and KYC rule validation pipeline execution.
        
        Orchestrates:
        1. Tenant-isolated async database session creation.
        2. Loading target KycCase and CaseDocument records.
        3. Reading stored document bytes from LocalStorageService.
        4. Invoking MultiTierOCREngine for automated field extraction.
        5. Persisting ExtractedField entities linked to documents.
        6. Aggregating extracted KYC criteria and executing KYCValidationEngine.
        7. Persisting validation issues to KycCase.validation_issues and logging AuditEvent.
        """
        factory = session_factory or self.session_factory or async_session_maker
        try:
            with tenant_context(tenant_id):
                async with factory() as session:
                    # 1. Fetch case with strict tenant scoping
                    stmt_case = select(KycCase).where(
                        KycCase.id == case_id,
                        KycCase.tenant_id == tenant_id,
                    )
                    case = (await session.execute(stmt_case)).scalar_one_or_none()
                    if not case:
                        logger.warning(
                            "Background pipeline: Case %s not found for tenant %s",
                            case_id,
                            tenant_id,
                        )
                        return

                    # 2. Fetch associated applicant for cross-validation
                    applicant = None
                    if case.applicant_id:
                        stmt_app = select(Applicant).where(
                            Applicant.id == case.applicant_id,
                            Applicant.tenant_id == tenant_id,
                        )
                        applicant = (await session.execute(stmt_app)).scalar_one_or_none()

                    # 3. Load documents
                    if not doc_ids:
                        return
                    stmt_docs = select(CaseDocument).where(
                        CaseDocument.id.in_(doc_ids),
                        CaseDocument.tenant_id == tenant_id,
                    )
                    docs = (await session.execute(stmt_docs)).scalars().all()
                    if not docs:
                        logger.warning(
                            "Background pipeline: No documents found for IDs %s", doc_ids
                        )
                        return

                    # 4. OCR Extraction across documents
                    all_extracted_fields: List[ExtractedField] = []
                    field_values_map: dict[str, str] = {}

                    for doc in docs:
                        try:
                            file_bytes = self.storage.read_file(doc.storage_key)
                        except Exception as read_err:
                            logger.error(
                                "Background pipeline: Failed reading storage_key '%s': %s",
                                doc.storage_key,
                                read_err,
                            )
                            continue

                        ocr_result = await ocr_engine.extract_fields(
                            document_type=doc.document_type,
                            file_bytes=file_bytes,
                        )

                        for f in ocr_result.extracted_fields:
                            ef = ExtractedField(
                                id=uuid.uuid4(),
                                tenant_id=tenant_id,
                                document_id=doc.id,
                                field_name=f.field_name,
                                draft_value=f.draft_value,
                                confirmed_value=None,
                                source_page=f.source_page,
                                confidence=f.confidence,
                                applicant_confirmed=False,
                                reviewer_decision="pending",
                                correction_history=[],
                            )
                            session.add(ef)
                            all_extracted_fields.append(ef)
                            if f.draft_value and f.field_name not in field_values_map:
                                field_values_map[f.field_name] = f.draft_value

                    await session.flush()

                    # 5. Execute KYC Validation Engine
                    applicant_type = case.case_type if case.case_type else "person"
                    app_name = applicant.full_name if (applicant and hasattr(applicant, "full_name")) else None
                    if not app_name and applicant:
                        app_name = f"{applicant.first_name or ''} {applicant.last_name or ''}".strip() or applicant.business_name
                    val_result = validation_engine.validate(
                        aadhaar_number=field_values_map.get("aadhaar_number"),
                        pan_number=field_values_map.get("pan_number"),
                        passport_mrz=field_values_map.get("passport_mrz"),
                        dl_number=field_values_map.get("dl_number"),
                        date_of_birth=field_values_map.get("date_of_birth"),
                        expiry_date=field_values_map.get("expiry_date"),
                        applicant_name=app_name,
                        extracted_name=field_values_map.get("full_name"),
                        applicant_type=applicant_type,
                    )

                    # 6. Persist validation issues to case
                    case.validation_issues = [
                        {
                            "code": iss.code,
                            "field_name": iss.field_name,
                            "severity": iss.severity,
                            "message": iss.message,
                        }
                        for iss in val_result.issues
                    ]

                    # 7. Audit log background processing completion
                    audit = AuditEvent(
                        tenant_id=tenant_id,
                        action="background_pipeline_completed",
                        resource_type="case",
                        resource_id=case.id,
                        metadata_={
                            "case_number": case.case_number,
                            "documents_processed": len(docs),
                            "fields_extracted": len(all_extracted_fields),
                            "is_valid": val_result.is_valid,
                            "error_count": val_result.error_count,
                            "warning_count": val_result.warning_count,
                            "recommendation": val_result.recommendation,
                        },
                    )
                    session.add(audit)

                    await session.commit()
                    logger.info(
                        "Background pipeline completed for case %s (%s docs, %s fields, recommendation=%s)",
                        case.case_number,
                        len(docs),
                        len(all_extracted_fields),
                        val_result.recommendation,
                    )
        except Exception as exc:
            logger.exception(
                "Background pipeline encountered an unhandled exception for case %s: %s",
                case_id,
                exc,
            )


email_intake_service = EmailIntakeService()
