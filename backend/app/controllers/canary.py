import hashlib
import secrets
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Annotated, Any, Dict, List

from bson import ObjectId
from bson.errors import InvalidId
from litestar import Controller, Request, Response, Router, delete, get, post, put
from litestar.background_tasks import BackgroundTask
from litestar.contrib.jwt import Token
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body

from app.env import SETTINGS
from app.errors import (
    CanaryAlreadyTrusted,
    CanaryNotFoundException,
    CanaryTaken,
    DomainValidationError,
    InvalidBlake2Hash,
    PublishedWarrantNotFoundException,
    TooManyFiles,
)
from app.lib.canary import Canary
from app.lib.key_bulders import logged_in_user_key_builder
from app.lib.otp import OneTimePassword
from app.lib.s3 import s3_upload_file
from app.lib.user import User
from app.models.canary import (
    CanaryModel,
    CreateCanaryModel,
    CreateCanaryWarrantModel,
    CreatedCanaryWarrantModel,
    NextCanaryEnum,
    PublicCanaryModel,
    PublishCanaryWarrantModel,
    PublishedCanaryWarrantModel,
    TrustedCanaryModel,
)

if TYPE_CHECKING:
    from custom_types import State


@post(
    path="/create",
    description="Create a canary for a given domain",
    tags=["canary"],
)
async def create_canary(
    data: CreateCanaryModel, state: "State", request: Request[ObjectId, Token, Any]
) -> CanaryModel:
    domain = data.domain.lower().strip()

    if (
        await state.mongo.canary.count_documents(
            {
                "$or": [
                    {"domain": domain, "domain_verification.completed": True},
                    {"domain": domain, "user_id": request.user},
                ]
            }
        )
        > 0
        or await state.mongo.deleted_canary.count_documents(
            {"domain_hash": hashlib.sha256(domain.encode()).hexdigest()}
        )
        > 0
    ):
        raise CanaryTaken()

    to_insert = {
        **data.model_dump(),
        "domain": domain,
        "user_id": request.user,
        "created": datetime.utcnow(),
        "logo": None,
        "domain_verification": {"completed": False, "code": secrets.token_urlsafe(32)},
    }

    await state.mongo.canary.insert_one(to_insert)

    return CanaryModel(**to_insert)


@get(
    "/list",
    description="List canaries for user",
    tags=["canary"],
    cache_key_builder=logged_in_user_key_builder,
)
async def list_canaries(
    request: Request[ObjectId, Token, Any], state: "State"
) -> List[CanaryModel]:
    canaries: List[CanaryModel] = []
    async for canary in state.mongo.canary.find({"user_id": request.user}):
        canaries.append(CanaryModel(**canary))

    return canaries


@get("/trusted/list", description="List trusted canaries", tags=["canary"])
async def list_trusted_canaries(
    request: Request[ObjectId, Token, Any], state: "State"
) -> Dict[str, TrustedCanaryModel]:
    trusted_canaries: Dict[str, TrustedCanaryModel] = {}

    async for trusted in state.mongo.trusted_canary.find({"user_id": request.user}):
        trusted_canaries[trusted["domain"]] = TrustedCanaryModel(**trusted)

    return trusted_canaries


@get(
    "/published/{canary_id:str}/{page:int}",
    description="Get a canary warrant",
    tags=["canary", "warrant"],
    exclude_from_auth=True,
)
async def published_warrant(
    state: "State", canary_id: str, page: int = 0
) -> PublishedCanaryWarrantModel:
    try:
        canary_object_id = ObjectId(canary_id)
    except InvalidId:
        raise PublishedWarrantNotFoundException()

    warrant = await state.mongo.canary_warrant.find_one(
        {"canary_id": canary_object_id, "published": True},
        sort=[("_id", -1)],
        skip=page,
    )
    if not warrant:
        raise PublishedWarrantNotFoundException()

    return PublishedCanaryWarrantModel(**warrant)


class PublishCanary(Controller):
    path = "/warrant/{warrant_id:str}"

    @post(
        "/document/{hash_:str}",
        description="Upload a canary warrant document",
        tags=["canary", "warrant", "document"],
    )
    async def upload_document(
        self,
        request: Request[ObjectId, Token, Any],
        state: "State",
        warrant_id: str,
        hash_: str,
        data: Annotated[
            # Annoying has to be a list, otherwise schema error.
            List[UploadFile],
            Body(media_type=RequestEncodingType.MULTI_PART),
        ],
    ) -> None:
        if len(hash_) > 64:
            raise InvalidBlake2Hash()

        try:
            id_ = ObjectId(warrant_id)
        except InvalidId:
            raise PublishedWarrantNotFoundException()

        warrant = await state.mongo.canary_warrant.find_one(
            {"_id": id_, "user_id": request.user, "published": False}
        )
        if not warrant:
            raise PublishedWarrantNotFoundException()

        if len(warrant["documents"]) >= SETTINGS.canary.documents.max_amount:
            raise TooManyFiles()

        uploaded_file = await s3_upload_file(
            data[0],
            ("canary", "documents"),
            max_size=SETTINGS.canary.documents.max_size,
            allowed_extensions=SETTINGS.canary.documents.allowed_extensions,
        )

        await state.mongo.canary_warrant.update_one(
            {"_id": id_, "user_id": request.user, "active": False},
            {
                "$push": {
                    "documents": {
                        "hash": hash_,
                        "filename": data[0].filename,
                        "file_id": uploaded_file.file_id,
                        "size": uploaded_file.size,
                    }
                }
            },
        )

    @post("/publish", description="Publish a canary", tags=["canary", "warrant"])
    async def publish(
        self,
        request: Request[ObjectId, Token, Any],
        state: "State",
        warrant_id: str,
        data: PublishCanaryWarrantModel,
    ) -> Response:
        try:
            id_ = ObjectId(warrant_id)
        except InvalidId:
            raise PublishedWarrantNotFoundException()

        warrant = await state.mongo.canary_warrant.find_one(
            {"_id": id_, "user_id": request.user, "published": False}
        )
        if not warrant:
            raise PublishedWarrantNotFoundException()

        to_set = {
            **data.model_dump(),
            "concern": data.concern.value,
            "active": True,
            "published": True,
        }

        await state.mongo.canary_warrant.update_one(
            {
                "_id": id_,
                "user_id": request.user,
                "active": False,
            },
            {
                "$set": to_set,
            },
        )

        await state.mongo.canary_warrant.update_many(
            {"canary_id": warrant["canary_id"], "_id": {"$ne": id_}},
            {"$set": {"active": False}},
        )

        return Response(
            None,
            background=BackgroundTask(
                Canary(state, warrant["canary_id"]).alert_subscribers,
                warrant=PublishedCanaryWarrantModel(
                    **{**warrant, **to_set}
                ).model_dump(),
            ),
        )


class CanarySubscription(Controller):
    path = "/subscription/{canary_id:str}"

    @get(
        "/",
        description="Check if user is subscribed to a canary",
        tags=["canary", "subscription"],
    )
    async def am_subscribed(
        self, request: Request[ObjectId, Token, Any], state: "State", canary_id: str
    ) -> bool:
        try:
            id_ = ObjectId(canary_id)
        except InvalidId:
            return False

        return (
            await state.mongo.subscribed_canary.count_documents(
                {"user_id": request.user, "canary_id": id_}
            )
            > 0
        )

    @delete(
        "/unsubscribe",
        description="Unsubscribe from a canary",
        tags=["canary", "subscription"],
    )
    async def unsubscribe(
        self,
        request: Request[ObjectId, Token, Any],
        state: "State",
        canary_id: str,
    ) -> None:
        try:
            id_ = ObjectId(canary_id)
        except InvalidId:
            return

        await state.mongo.subscribed_canary.delete_one(
            {
                "user_id": request.user,
                "canary_id": id_,
            }
        )

    @post(
        "/subscribe",
        description="Subscribe to a canary",
        tags=["canary", "subscription"],
    )
    async def subscribe(
        self,
        request: Request[ObjectId, Token, Any],
        state: "State",
        canary_id: str,
    ) -> None:
        try:
            id_ = ObjectId(canary_id)
        except InvalidId:
            return

        if (
            await state.mongo.subscribed_canary.count_documents(
                {"user_id": request.user, "canary_id": id_}
            )
            == 0
        ):
            await state.mongo.subscribed_canary.insert_one(
                {
                    "user_id": request.user,
                    "canary_id": id_,
                }
            )


class CanaryController(Controller):
    path = "/{domain:str}"

    @post(
        "/create/warrant",
        description="Create a warrant for a canary",
        tags=["canary", "warrant"],
    )
    async def create_warrant(
        self,
        request: Request[ObjectId, Token, Any],
        state: "State",
        domain: str,
        data: CreateCanaryWarrantModel,
        otp: str,
    ) -> CreatedCanaryWarrantModel:
        canary = await Canary(state, domain).user(request.user).get()
        if not canary.domain_verification.completed:
            raise DomainValidationError()

        user = await User(state, request.user).get()
        await OneTimePassword.validate_user(state, user, otp)

        now: datetime = datetime.utcnow()
        match data.next_:
            case NextCanaryEnum.tomorrow:
                next_canary = now + timedelta(days=1)
            case NextCanaryEnum.week:
                next_canary = now + timedelta(days=7)
            case NextCanaryEnum.fortnight:
                next_canary = now + timedelta(days=14)
            case NextCanaryEnum.month:
                next_canary = now + timedelta(days=30)
            case NextCanaryEnum.quarter:
                next_canary = now + timedelta(days=90)
            case _:
                next_canary = now + timedelta(days=365)

        created_warrant = {
            "user_id": request.user,
            "canary_id": canary.id,
            "next_canary": next_canary,
            "issued": now,
            "active": False,
            "documents": [],
            "published": False,
        }

        await state.mongo.canary_warrant.insert_one(created_warrant)

        return CreatedCanaryWarrantModel(**created_warrant)

    @get(
        "/trusted",
        description="Get signed public key hash for a trusted canary",
        tags=["canary"],
    )
    async def get_trusted(
        self, request: Request[ObjectId, Token, Any], state: "State", domain: str
    ) -> TrustedCanaryModel:
        trusted = await state.mongo.trusted_canary.find_one(
            {"user_id": request.user, "domain": domain}
        )
        if not trusted:
            raise CanaryNotFoundException()

        return TrustedCanaryModel(**trusted)

    @post(
        "/trusted/add",
        description="Saves a canary as a trusted canary",
        tags=["canary"],
    )
    async def trust_canary(
        self,
        request: Request[ObjectId, Token, Any],
        state: "State",
        data: TrustedCanaryModel,
        domain: str,
    ) -> None:
        try:
            await Canary(state, domain).exists()
        except CanaryNotFoundException:
            raise

        if (
            await state.mongo.trusted_canary.count_documents(
                {"user_id": request.user, "domain": domain}
            )
            > 0
        ):
            raise CanaryAlreadyTrusted()

        trusted = {"user_id": request.user, "domain": domain, **data.model_dump()}
        await state.mongo.trusted_canary.insert_one(trusted)

    @post(
        "/verify",
        cache=60,
        description="Verify domain ownership via DNS",
        tags=["canary"],
    )
    async def verify(
        self, domain: str, request: Request[ObjectId, Token, Any], state: "State"
    ) -> Response:
        try:
            await Canary(state, domain).user(request.user).attempt_verify()
        except DomainValidationError:
            raise

        return Response(content=None, status_code=200)

    @delete("/delete", description="Delete a canary", tags=["canary"])
    async def delete_canary(
        self,
        domain: str,
        request: Request[ObjectId, Token, Any],
        state: "State",
        otp: str,
    ) -> None:
        user = await User(state, request.user).get()
        await OneTimePassword.validate_user(state, user, otp)

        await Canary(state, domain).user(request.user).delete()

    @get(
        "/public",
        description="Get public details about canary",
        tags=["canary"],
        exclude_from_auth=True,
        cache=120,
    )
    async def public_canary(self, domain: str, state: "State") -> PublicCanaryModel:
        return await Canary(state, domain).get()

    @get("/", description="Get private details about a canary", tags=["canary"])
    async def get_canary(
        self, domain: str, request: Request[ObjectId, Token, Any], state: "State"
    ) -> CanaryModel:
        return await Canary(state, domain).user(request.user).get()

    @post("/logo/update", description="Update logo for given domain", tags=["canary"])
    async def update_logo(
        self,
        domain: str,
        request: Request[ObjectId, Token, Any],
        state: "State",
        data: Annotated[
            List[UploadFile], Body(media_type=RequestEncodingType.MULTI_PART)
        ],
    ) -> None:
        canary = await Canary(state, domain).user(request.user).get()

        uploaded_file = await s3_upload_file(
            data[0],
            ("canary", "logos"),
            max_size=SETTINGS.canary.logo.max_size,
            allowed_extensions=SETTINGS.canary.logo.allowed_extensions,
            filename=str(canary.id),
        )

        await state.mongo.canary.update_one(
            {"_id": canary.id}, {"$set": {"logo": uploaded_file.file_id}}
        )


router = Router(
    path="/canary",
    route_handlers=[
        create_canary,
        list_canaries,
        list_trusted_canaries,
        published_warrant,
        PublishCanary,
        CanaryController,
        CanarySubscription,
    ],
)
