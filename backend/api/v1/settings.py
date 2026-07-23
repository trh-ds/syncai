from fastapi import APIRouter
from pydantic import BaseModel, Field

from core.config import settings

router = APIRouter(tags=["settings"])


class SettingsOut(BaseModel):
    mail_mode: str
    poll_interval: int
    gmail_configured: bool
    gmail_user: str


class SettingsPatch(BaseModel):
    mail_mode: str = Field(default="hitl", pattern="^(auto|hitl)$")


@router.get("/settings", response_model=SettingsOut)
def get_settings():
    return SettingsOut(
        mail_mode=settings.MAIL_MODE,
        poll_interval=settings.MAIL_POLL_INTERVAL,
        gmail_configured=settings.gmail_configured,
        gmail_user=settings.GMAIL_USER_EMAIL,
    )


@router.patch("/settings", response_model=SettingsOut)
def patch_settings(patch: SettingsPatch):
    settings.MAIL_MODE = patch.mail_mode  # ponytail: mutable singleton, fine for single-tenant
    return SettingsOut(
        mail_mode=settings.MAIL_MODE,
        poll_interval=settings.MAIL_POLL_INTERVAL,
        gmail_configured=settings.gmail_configured,
        gmail_user=settings.GMAIL_USER_EMAIL,
    )
