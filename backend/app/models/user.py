from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

import pyotp
from argon2.profiles import RFC_9106_LOW_MEMORY
from bson import ObjectId
from pydantic import AnyUrl, BaseModel, EmailStr, Field

from app.env import SETTINGS
from app.models.customs import CustomJsonEncoder, IvField


class NotificationEnum(Enum):
    canary_renewals = "canary_renewals"
    canary_subscriptions = "canary_subscriptions"
    survey_submissions = "survey_submissions"


class WebhookModel(BaseModel):
    url: AnyUrl
    type: NotificationEnum


class EmailModel(BaseModel):
    email: EmailStr


class Argon2Modal(BaseModel):
    salt: str = Field(
        ...,
        max_length=64,
        description="Salt used for deriving account key, base64 encoded",
    )
    time_cost: int = Field(
        RFC_9106_LOW_MEMORY.time_cost,
        ge=RFC_9106_LOW_MEMORY.time_cost - 1,
        le=12,
        description="Time cost",
    )
    memory_cost: int = Field(
        RFC_9106_LOW_MEMORY.memory_cost,
        ge=RFC_9106_LOW_MEMORY.memory_cost - 1,
        le=3355443200,
        description="Memory cost",
    )


class PublicUserModel(BaseModel):
    kdf: Argon2Modal
    otp_completed: bool = False


class AccountAuthModal(BaseModel):
    public_key: str = Field(
        ..., max_length=44, description="ed25519 public key, base64 encoded"
    )


class AccountEd25199Modal(IvField):
    public_key: str = Field(
        ..., max_length=44, description="ed25519 public key, base64 encoded"
    )
    cipher_text: str = Field(
        ...,
        max_length=240,
        description="ed25519 private key, encrypted with keychain, base64 encoded",
    )


class AccountX25519Model(IvField):
    public_key: str = Field(
        ..., max_length=44, description="X25519 public key, base64 encoded"
    )
    cipher_text: str = Field(
        ...,
        max_length=240,
        description="X25519 private key, encrypted with keychain, base64 encoded",
    )


class AccountKeychainModal(IvField):
    cipher_text: str = Field(
        ...,
        max_length=82,
        description="Locally encrypted 32 byte key for keychain, base64 encoded",
    )


class AccountUpdatePassword(BaseModel):
    auth: AccountAuthModal
    keypair: AccountX25519Model
    sign_keypair: AccountEd25199Modal
    keychain: AccountKeychainModal
    kdf: Argon2Modal
    signature: str = Field(
        ...,
        max_length=128,
        description="Locally signed with ed25519 private key to validate account data hasn't been changed. Base64 encoded",
    )  # Used for the client to validate our response.


class __CreateUserShared(EmailModel, AccountUpdatePassword):
    ip_lookup_consent: bool = False

    # Assumed client side algorithms being used, help for future proofing
    # if we need to move away from outdated algorithms.
    algorithms: str = Field(
        "XChaCha20Poly1305+ED25519+Argon2+X25519_XSalsa20Poly1305+BLAKE2b+IV24+SALT16+KEY32",
        max_length=120,
        description="Algorithms used by client.",
    )


class CreateUserModel(__CreateUserShared):
    pass


class OtpModel(BaseModel):
    secret: Optional[str] = None
    provisioning_uri: Optional[str] = None
    completed: bool = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.provisioning_uri = self.__provisioning_uri()

    def __provisioning_uri(self) -> Optional[str]:
        if not self.secret:
            return

        return pyotp.totp.TOTP(self.secret).provisioning_uri(
            issuer_name=SETTINGS.site_name, name=SETTINGS.site_name
        )


class NotificationsModel(CustomJsonEncoder):
    email: List[NotificationEnum] = Field(..., max_length=3)
    webhooks: Dict[NotificationEnum, List[str]]
    push: Dict[NotificationEnum, str] = {}


class UserModel(__CreateUserShared, EmailModel, CustomJsonEncoder):
    id: ObjectId = Field(..., alias="_id")
    created: datetime
    otp: OtpModel
    email_verified: bool = False
    notifications: NotificationsModel


class UserLoginSignatureModel(BaseModel):
    signature: str = Field(
        ..., description="to_sign signed with ed25519 private key, base64 encoded"
    )
    one_day_login: bool = Field(
        False, description="Overwrites the default JWT expire days to only one day"
    )
    id: str = Field(..., alias="_id")


class UserToSignModel(CustomJsonEncoder):
    to_sign: str = Field(..., description="to be signed with ed25519 private key")
    id: ObjectId = Field(..., alias="_id")


class NftyNotificationModel(BaseModel):
    topic: str
    url: str
