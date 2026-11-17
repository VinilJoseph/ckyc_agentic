"""API Router Aggregator for v1"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, cases, documents, intake, tenants, verification

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["Tenants"])
api_router.include_router(cases.router, prefix="/cases", tags=["KYC Cases"])
api_router.include_router(documents.router, tags=["Documents"])
api_router.include_router(verification.router, tags=["Verification"])
api_router.include_router(intake.router, tags=["Email Intake & Exceptions"])
