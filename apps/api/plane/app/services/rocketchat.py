# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Rocket.Chat admin API client + Oneplace sync helpers."""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Optional

import requests

from plane.db.models import User, Workspace, WorkspaceMember
from plane.db.models.rocketchat import RocketChatUserLink, RocketChatWorkspaceLink
from plane.utils.exception_logger import log_exception

logger = logging.getLogger("plane.rocketchat")


def rocketchat_enabled() -> bool:
    return os.environ.get("ROCKETCHAT_ENABLED", "1") == "1" and bool(
        os.environ.get("ROCKETCHAT_URL") or os.environ.get("ROCKETCHAT_ROOT_URL")
    )


def _base_url() -> str:
    # Prefer internal Docker URL for server-to-server calls.
    # When ROOT_URL includes /chat, the Meteor app (and /api/v1) is mounted under /chat.
    base = (os.environ.get("ROCKETCHAT_URL") or "http://rocketchat:3000").rstrip("/")
    root = (os.environ.get("ROCKETCHAT_ROOT_URL") or "").rstrip("/")
    if root.endswith("/chat") and not base.endswith("/chat"):
        return f"{base}/chat"
    return base


def _public_root() -> str:
    return (os.environ.get("ROCKETCHAT_ROOT_URL") or "https://oneplace.roinetinsurance.in/chat").rstrip("/")


class RocketChatClient:
    def __init__(self) -> None:
        self.base_url = _base_url()
        self.user_id = os.environ.get("ROCKETCHAT_ADMIN_USER_ID", "")
        self.auth_token = os.environ.get("ROCKETCHAT_ADMIN_TOKEN", "")
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    def _ensure_auth(self) -> None:
        if self.user_id and self.auth_token:
            self._session.headers["X-User-Id"] = self.user_id
            self._session.headers["X-Auth-Token"] = self.auth_token
            return
        username = os.environ.get("ROCKETCHAT_ADMIN_USER", "")
        password = os.environ.get("ROCKETCHAT_ADMIN_PASSWORD", "")
        if not username or not password:
            raise RuntimeError(
                "Rocket.Chat admin credentials missing. Set ROCKETCHAT_ADMIN_TOKEN + "
                "ROCKETCHAT_ADMIN_USER_ID, or ROCKETCHAT_ADMIN_USER + ROCKETCHAT_ADMIN_PASSWORD."
            )
        res = self._session.post(
            f"{self.base_url}/api/v1/login",
            json={"user": username, "password": password},
            timeout=30,
        )
        res.raise_for_status()
        data = res.json().get("data") or {}
        self.auth_token = data.get("authToken") or ""
        self.user_id = data.get("userId") or ""
        if not self.auth_token or not self.user_id:
            raise RuntimeError("Rocket.Chat login did not return authToken/userId")
        self._session.headers["X-User-Id"] = self.user_id
        self._session.headers["X-Auth-Token"] = self.auth_token

    def request(self, method: str, path: str, **kwargs: Any) -> dict:
        self._ensure_auth()
        url = f"{self.base_url}{path}"
        res = self._session.request(method, url, timeout=kwargs.pop("timeout", 30), **kwargs)
        if res.status_code >= 400:
            logger.warning("Rocket.Chat %s %s -> %s %s", method, path, res.status_code, res.text[:500])
        res.raise_for_status()
        payload = res.json()
        if isinstance(payload, dict) and payload.get("success") is False:
            raise RuntimeError(payload.get("error") or "Rocket.Chat API error")
        return payload if isinstance(payload, dict) else {"data": payload}


def _sanitize_username(email: str, fallback: str) -> str:
    base = (email.split("@")[0] if email else fallback) or "user"
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "", base).lower()
    if not cleaned:
        cleaned = "user"
    return cleaned[:40]


def ensure_rc_user(client: RocketChatClient, user: User) -> RocketChatUserLink:
    try:
        link = RocketChatUserLink.objects.get(user=user)
        return link
    except RocketChatUserLink.DoesNotExist:
        pass

    email = (user.email or "").strip()
    username = _sanitize_username(email, str(user.id)[:8])
    name = user.display_name or user.first_name or username

    # Try info by username / email first
    existing_id = None
    try:
        info = client.request("GET", f"/api/v1/users.info?username={username}")
        existing_id = (info.get("user") or {}).get("_id")
    except Exception:
        pass
    if not existing_id and email:
        try:
            info = client.request("GET", f"/api/v1/users.info?username={email}")
            existing_id = (info.get("user") or {}).get("_id")
        except Exception:
            pass

    if not existing_id:
        # Ensure unique username
        candidate = username
        for i in range(20):
            try:
                created = client.request(
                    "POST",
                    "/api/v1/users.create",
                    json={
                        "email": email or f"{candidate}@oneplace.local",
                        "name": name,
                        "username": candidate,
                        "password": os.environ.get("ROCKETCHAT_DEFAULT_USER_PASSWORD", "ChangeMeOnce!23"),
                        "verified": True,
                        "requirePasswordChange": False,
                        "joinDefaultChannels": False,
                    },
                )
                existing_id = (created.get("user") or {}).get("_id")
                username = candidate
                break
            except Exception:
                candidate = f"{username}{i + 1}"[:40]
        if not existing_id:
            raise RuntimeError(f"Failed to create Rocket.Chat user for {user.id}")

    link, _ = RocketChatUserLink.objects.update_or_create(
        user=user,
        defaults={"rc_user_id": existing_id, "rc_username": username},
    )
    return link


def ensure_rc_team(client: RocketChatClient, workspace: Workspace) -> RocketChatWorkspaceLink:
    try:
        return RocketChatWorkspaceLink.objects.get(workspace=workspace)
    except RocketChatWorkspaceLink.DoesNotExist:
        pass

    team_name = re.sub(r"[^a-zA-Z0-9_-]", "-", workspace.slug).strip("-")[:50] or str(workspace.id)[:8]
    # Check existing teams by name
    try:
        listed = client.request("GET", "/api/v1/teams.list")
        for team in listed.get("teams") or []:
            if team.get("name") == team_name:
                link, _ = RocketChatWorkspaceLink.objects.update_or_create(
                    workspace=workspace,
                    defaults={
                        "rc_team_id": team.get("_id"),
                        "rc_team_name": team_name,
                        "rc_room_id": team.get("roomId") or "",
                    },
                )
                return link
    except Exception as exc:
        log_exception(exc)

    created = client.request(
        "POST",
        "/api/v1/teams.create",
        json={"name": team_name, "type": 1, "members": []},
    )
    team = created.get("team") or {}
    link, _ = RocketChatWorkspaceLink.objects.update_or_create(
        workspace=workspace,
        defaults={
            "rc_team_id": team.get("_id") or "",
            "rc_team_name": team_name,
            "rc_room_id": team.get("roomId") or "",
        },
    )
    return link


def ensure_team_membership(client: RocketChatClient, workspace: Workspace, user: User) -> None:
    user_link = ensure_rc_user(client, user)
    team_link = ensure_rc_team(client, workspace)
    try:
        client.request(
            "POST",
            "/api/v1/teams.addMembers",
            json={
                "teamId": team_link.rc_team_id,
                "members": [{"userId": user_link.rc_user_id, "roles": ["member"]}],
            },
        )
    except Exception as exc:
        # Already a member is fine
        logger.info("teams.addMembers for %s: %s", user.id, exc)


def remove_team_membership(client: RocketChatClient, workspace: Workspace, user: User) -> None:
    try:
        user_link = RocketChatUserLink.objects.get(user=user)
        team_link = RocketChatWorkspaceLink.objects.get(workspace=workspace)
    except (RocketChatUserLink.DoesNotExist, RocketChatWorkspaceLink.DoesNotExist):
        return
    try:
        client.request(
            "POST",
            "/api/v1/teams.removeMember",
            json={"teamId": team_link.rc_team_id, "userId": user_link.rc_user_id},
        )
    except Exception as exc:
        log_exception(exc)


def _hash_login_token(token: str) -> str:
    """Meteor Accounts._hashLoginToken — base64(sha256(token))."""
    import base64
    import hashlib

    digest = hashlib.sha256(token.encode("utf-8")).digest()
    return base64.b64encode(digest).decode("ascii")


def _mint_resume_token_via_mongo(rc_user_id: str) -> str:
    """
    Mint a Meteor resume login token in Rocket.Chat Mongo.

    users.createToken is restricted on Rocket.Chat 7 CE; writing
    services.resume.loginTokens is the supported SSO-without-OAuth path.
    """
    import secrets
    from datetime import datetime, timezone

    try:
        from pymongo import MongoClient
    except ImportError as exc:
        raise RuntimeError("pymongo is required for Rocket.Chat SSO token minting") from exc

    mongo_url = os.environ.get(
        "ROCKETCHAT_MONGO_URL",
        "mongodb://rocketchat-mongo:27017/rocketchat?replicaSet=rs0",
    )
    token = secrets.token_urlsafe(43)
    hashed = _hash_login_token(token)
    client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
    try:
        result = client.get_default_database().users.update_one(
            {"_id": rc_user_id},
            {
                "$push": {
                    "services.resume.loginTokens": {
                        "hashedToken": hashed,
                        "when": datetime.now(timezone.utc),
                    }
                }
            },
        )
        if result.matched_count != 1:
            raise RuntimeError(f"Rocket.Chat user {rc_user_id} not found in Mongo for SSO token")
    finally:
        client.close()
    return token


def create_login_token(client: RocketChatClient, user: User) -> str:
    user_link = ensure_rc_user(client, user)
    # Prefer admin API when available; fall back to Mongo resume tokens (RC 7 CE).
    try:
        payload = client.request(
            "POST",
            "/api/v1/users.createToken",
            json={"userId": user_link.rc_user_id},
        )
        data = payload.get("data") or payload
        token = data.get("authToken") or data.get("token")
        if token:
            return token
    except Exception as exc:
        logger.info("users.createToken unavailable, using Mongo resume token: %s", exc)
    return _mint_resume_token_via_mongo(user_link.rc_user_id)


def sync_workspace_member(workspace: Workspace, user: User, *, remove: bool = False) -> None:
    if not rocketchat_enabled():
        return
    try:
        client = RocketChatClient()
        if remove:
            remove_team_membership(client, workspace, user)
        else:
            ensure_team_membership(client, workspace, user)
    except Exception as exc:
        log_exception(exc)


def rename_rc_team(workspace: Workspace) -> None:
    """Best-effort rename of the RC team when workspace slug/name changes."""
    if not rocketchat_enabled():
        return
    try:
        link = RocketChatWorkspaceLink.objects.get(workspace=workspace)
    except RocketChatWorkspaceLink.DoesNotExist:
        return
    new_name = re.sub(r"[^a-zA-Z0-9_-]", "-", workspace.slug).strip("-")[:50] or str(workspace.id)[:8]
    if new_name == link.rc_team_name:
        return
    try:
        client = RocketChatClient()
        client.request(
            "POST",
            "/api/v1/teams.update",
            json={"teamId": link.rc_team_id, "data": {"name": new_name}},
        )
        link.rc_team_name = new_name
        link.save(update_fields=["rc_team_name", "updated_at"])
    except Exception as exc:
        log_exception(exc)


def sync_workspace(workspace: Workspace, owner: Optional[User] = None) -> None:
    if not rocketchat_enabled():
        return
    try:
        client = RocketChatClient()
        ensure_rc_team(client, workspace)
        if owner:
            ensure_team_membership(client, workspace, owner)
        for membership in WorkspaceMember.objects.filter(workspace=workspace, is_active=True).select_related(
            "member"
        ):
            if membership.member_id and not membership.member.is_bot:
                ensure_team_membership(client, workspace, membership.member)
    except Exception as exc:
        log_exception(exc)


def sso_redirect_url(user: User, workspace: Workspace) -> str:
    client = RocketChatClient()
    ensure_team_membership(client, workspace, user)
    token = create_login_token(client, user)
    root = _public_root()
    # resumeToken login (Meteor / Rocket.Chat)
    return f"{root}/home?resumeToken={token}"
