from typing import Annotated

from fastapi import APIRouter, Cookie, Response

from .. import config
from ..deps import SESSION_COOKIE, Conn, CurrentUser
from ..schemas import LoginIn
from ..services import auth as service

router = APIRouter(tags=["登录"])


@router.post("/login")
def login(body: LoginIn, response: Response, conn: Conn):
    user, token = service.login(conn, body.username, body.password)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=config.SESSION_HOURS * 3600,
        httponly=True,   # JS 读不到，页面被注入脚本也偷不走
        samesite="lax",  # 别的网站发起的 POST 不带这个 cookie，防 CSRF
        secure=config.COOKIE_SECURE,
    )
    return user


@router.post("/logout", status_code=204)
def logout(response: Response, conn: Conn,
           session: Annotated[str | None, Cookie()] = None):
    if session:
        service.logout(conn, session)
    response.delete_cookie(SESSION_COOKIE)


@router.get("/me")
def me(user: CurrentUser):
    return user
