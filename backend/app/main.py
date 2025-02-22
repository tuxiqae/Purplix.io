from typing import TYPE_CHECKING, cast

import aiohttp
from litestar import Litestar
from litestar.channels import ChannelsPlugin
from litestar.channels.backends.redis import RedisChannelsPubSubBackend
from litestar.config.cors import CORSConfig
from litestar.config.csrf import CSRFConfig
from litestar.config.response_cache import ResponseCacheConfig
from litestar.datastructures import State
from litestar.middleware.rate_limit import RateLimitConfig
from litestar.openapi import OpenAPIConfig
from litestar.openapi.spec import License, Server
from litestar.stores.redis import RedisStore
from models.customs import TYPE_ENCODERS
from motor import motor_asyncio
from redis.asyncio import Redis

from app.controllers import routes
from app.env import SETTINGS
from app.lib.crontabs import CronTabs
from app.lib.jwt import jwt_cookie_auth
from app.tasks import tasks

if TYPE_CHECKING:
    from litestar.config.app import AppConfig

    from app.custom_types import State as StateType


redis = Redis(host=SETTINGS.redis.host, port=SETTINGS.redis.port, db=SETTINGS.redis.db)

redis_store = RedisStore(redis=redis)


async def init_tasks(app_config: "AppConfig") -> None:
    app_config.state.tasks = CronTabs(cast("StateType", app_config.state), tasks)
    app_config.state.tasks.start()


async def close_tasks(app_config: "AppConfig") -> None:
    if app_config.state.tasks:
        app_config.state.tasks.stop()


async def init_mongo(app_config: "AppConfig") -> None:
    await app_config.state.mongo.old_otp.create_index("expires", expireAfterSeconds=0)
    await app_config.state.mongo.proof.create_index("expires", expireAfterSeconds=0)
    await app_config.state.mongo.session.create_index(
        "record_kept_till", expireAfterSeconds=0
    )
    await app_config.state.mongo.email_verification.create_index(
        "expires", expireAfterSeconds=0
    )
    await app_config.state.mongo.survey_blocker.create_index(
        "expires", expireAfterSeconds=0
    )
    await app_config.state.mongo.canary_warrant.create_index(
        "issued",
        expireAfterSeconds=10800,  # 3 hours
        partialFilterExpression={"published": False},
    )


async def init_aiohttp(app_config: "AppConfig") -> None:
    app_config.state.aiohttp = aiohttp.ClientSession()


async def close_aiohttp(app_config: "AppConfig") -> None:
    await app_config.state.aiohttp.close()


async def wipe_cache_on_shutdown() -> None:
    await redis_store.delete_all()


app = Litestar(
    route_handlers=[routes],
    on_startup=[init_mongo, init_tasks, init_aiohttp],  # type: ignore
    on_shutdown=[close_aiohttp, wipe_cache_on_shutdown, close_tasks],  # type: ignore
    csrf_config=CSRFConfig(
        secret=SETTINGS.csrf_secret, cookie_httponly=False, cookie_samesite="strict"
    ),
    state=State(
        {
            "mongo": motor_asyncio.AsyncIOMotorClient(
                SETTINGS.mongo.host, SETTINGS.mongo.port
            )[SETTINGS.mongo.collection],
            "redis": redis_store,
            "aiohttp": None,
            "tasks": None,
        }
    ),
    middleware=[
        RateLimitConfig(
            rate_limit=("minute", 60),
            exclude=["/schema"],
            store="redis",
        ).middleware
    ],
    cors_config=CORSConfig(
        allow_origins=[
            SETTINGS.proxy_urls.backend,
            SETTINGS.proxy_urls.frontend,
            SETTINGS.proxy_urls.docs,
        ],
        allow_credentials=True,
    ),
    openapi_config=OpenAPIConfig(
        title=SETTINGS.open_api.title,
        # Disable all doc frontend endpoints.
        # Due to MITM attacks & malicious js concerns.
        enabled_endpoints={"openapi.json", "openapi.yaml"},
        license=License(
            name="GNU Affero General Public License v3.0",
            identifier="AGPL-3.0",
            url="https://github.com/WardPearce/Purplix.io/blob/main/LICENSE",
        ),
        terms_of_service=f"{SETTINGS.proxy_urls.frontend}/terms-of-service",
        version=SETTINGS.open_api.version,
        servers=[Server(url=SETTINGS.proxy_urls.backend, description="Production API")],
    ),
    stores={"redis": redis_store},
    plugins=[
        ChannelsPlugin(
            backend=RedisChannelsPubSubBackend(
                redis=redis,
            ),
            arbitrary_channels_allowed=True,
        )
    ],
    response_cache_config=ResponseCacheConfig(store="redis"),
    on_app_init=[jwt_cookie_auth.on_app_init],
    type_encoders=TYPE_ENCODERS,
    debug=SETTINGS.proxy_urls.frontend.endswith("localhost"),
)
