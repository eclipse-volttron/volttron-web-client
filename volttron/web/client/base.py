from __future__ import annotations
import logging
from pprint import pformat
from typing import Dict, Optional, Any
from urllib.parse import urlparse

import requests

from volttron.web.client.format_utls import get_header, get_footer

_log = logging.getLogger(__name__)


class AuthenticationError(Exception):
    pass


class Http:
    __auth__: Optional[Authentication] = None

    def check_auth(self):
        if not self.__auth__:
            raise AuthenticationError("Authentication not set.")

    def get_url(self, path: str):
        while path.startswith("/"):
            path = path[1:]
        return f"{self.__auth__.vui_url}/{path}"

    def get_headers(self, headers: Optional[Dict[str, str]] = None,  with_auth: bool = True) -> Dict[str, str]:
        if with_auth:
            self.check_auth()
            if headers is None:
                headers = {'Authorization': f'Bearer {self.__auth__.access_token}'}
            else:
                headers['Authorization'] = f'Bearer {self.__auth__.access_token}'

        if headers is None:
            headers = {}
        return headers

    def post(self, url: str, headers: Optional[Dict[str, str]] = None, auth_required: bool = True,
             json: Optional[Dict[str, Any]] = None, **kwargs):

        headers = self.get_headers(headers, auth_required)

        if json is not None:
            headers['Content-Type'] = 'application/json'

        return requests.post(url=url, headers=headers, json=json, **kwargs)

    def get(self, url: str, headers: Optional[Dict[str, str]] = None, auth_required: bool = True,
            **kwargs):
        _log.debug(get_header(f"GET {url}"))
        if not url.startswith("http"):
            url = self.get_url(url)
        headers = self.get_headers(headers, auth_required)
        response = requests.get(url=url, headers=headers, **kwargs)
        if response.ok:
            if response.headers.get('Content-Type') == 'application/json':
                _log.debug(pformat(response.json()))
            else:
                _log.debug(response.text)
        _log.debug(get_footer(f"END GET {url}"))
        return response

    def delete(self):
        pass

    def put(self):
        pass


class Authentication(Http):
    def __init__(self, auth_url: str, username: str, password: str, vui_url: Optional[str] = None):
        self._access_token: str
        self._refresh_token: str
        self._auth_url: str
        self._vui_url: str

        if self.__auth__ is None:
            response = self.post(url=auth_url, json={'username': username, 'password': password}, auth_required=False)
            if response.ok:
                self._access_token = response.json()['access_token']
                self._refresh_token = response.json()['refresh_token']
                Http.__auth__ = self

        self._auth_url = auth_url
        if not vui_url:
            parsed = urlparse(auth_url)
            self._vui_url = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
        else:
            self._vui_url = vui_url

    @property
    def refresh_token(self):
        return self._refresh_token

    @property
    def access_token(self):
        return self._access_token

    @property
    def vui_url(self):
        return self._vui_url

    @property
    def auth_url(self):
        return self._auth_url
