"""Thin wrapper around the azure-devops SDK that handles auth + connection."""
from __future__ import annotations

from functools import cached_property
from typing import Optional

from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication

from ado import config


class ADOClient:
    def __init__(self, org: Optional[str] = None, project: Optional[str] = None):
        # Store overrides; actual validation deferred to first API call
        self._org_override = org
        self._project_override = project

    @property
    def org(self) -> str:
        return self._org_override or config.require("org")

    @property
    def project(self) -> str:
        return self._project_override or config.require("project")

    @property
    def pat(self) -> str:
        return config.require("pat")

    @cached_property
    def _connection(self) -> Connection:
        org_url = f"https://dev.azure.com/{self.org}"
        creds = BasicAuthentication("", self.pat)
        return Connection(base_url=org_url, creds=creds)

    # --- clients ---

    @cached_property
    def git(self):
        return self._connection.clients.get_git_client()

    @cached_property
    def build(self):
        return self._connection.clients.get_build_client()

    @cached_property
    def work_item_tracking(self):
        return self._connection.clients.get_work_item_tracking_client()

    @cached_property
    def wiki(self):
        return self._connection.clients.get_wiki_client()

    @cached_property
    def core(self):
        return self._connection.clients.get_core_client()
