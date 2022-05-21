from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import List, Dict, Optional, Tuple, Any

from volttron.web.client.base import Http, AuthenticationError

_log = logging.getLogger(__name__)

LINK_IDENTIFIER = 'links'


class InvalidPlatformReference(Exception):
    pass


class InvalidAgentReference(Exception):
    pass

class InvalidRPCFunction(Exception):
    pass


@dataclass
class Link:
    key: str
    link: str


@dataclass
class Platform(Http):
    name: str
    links: List[Link] = field(default_factory=list)

    @property
    def agents(self) -> List[Agent]:
        agent_list: List[Agent] = []
        for link in self.links:
            if 'agents' == link.key:
                response = self.get(link.link, params={"agent-state": "installed"})
                if response.ok:
                    links = build_links(response.json()[LINK_IDENTIFIER])
                    for link in links:
                        agent_list.append(Agent(platform=self.name, identity=link.key, link=link.link))
                    break
        return agent_list

    @property
    def status(self) -> List[AgentStatus]:
        status = None
        contexts: List[AgentStatus] = []
        for link in self.links:
            if 'status' == link.key:
                status = self.get(link.link)
                for k, v in status.json().items():
                    contexts.append(AgentStatus(identity=k,
                                                name=v['name'],
                                                platform=self.name,
                                                exit_code=v['exit_code'],
                                                priority=v['priority'],
                                                running=v['running'],
                                                tag=v['tag'],
                                                uuid=v['uuid']))
        return status.json()

    def get_agent(self, identity: str) -> Agent:
        response = self.get(f"/vui/platforms/{self.name}/agents/{identity}")
        agent: Optional[Agent] = None
        if response.ok:
            agent = Agent(self.name, identity=identity, link=f"/vui/platforms/{self.name}/agents/{identity}")
        else:
            raise InvalidAgentReference()
        return agent


def build_links(kv: Dict[str, str]) -> List[Link]:
    links: List[Link] = []
    for k, v in kv.items():
        links.append(Link(k, v))
    return links


class Platforms(Http):

    def __init__(self):
        if not self.__auth__:
            raise AuthenticationError("Authenticate before accessing platforms.")

    def list(self) -> List[Platform]:
        response = self.get("/vui/platforms")
        platforms: List[Platform] = []
        if response.ok:
            # a link of platforms with key = platform name and
            # link a link to the specific platform
            pforms = build_links(response.json()[LINK_IDENTIFIER])
            for l in pforms:
                response = self.get(l.link)
                if response.ok:
                    l2 = build_links(response.json()[LINK_IDENTIFIER])
                    platforms.append(Platform(l.key, l2))
        return platforms

    def get_platform(self, name: str) -> Platform:
        response = super().get(f"/vui/platforms/{name}")
        platform: Optional[Platform] = None
        if response.ok:
            links = build_links(response.json()[LINK_IDENTIFIER])
            platform = Platform(name=name, links=links)
        else:
            raise InvalidPlatformReference()

        return platform


@dataclass
class Agent(Http):
    platform: str
    identity: str
    link: str

    @property
    def configs(self) -> Configs:
        response = self.get(self.link)
        links = build_links(response.json()[LINK_IDENTIFIER])
        configs = Configs(identity=self.identity, links=links)
        return configs

    @property
    def status(self) -> AgentStatus:
        response = self.get(url=f"{self.link}/status")
        obj = response.json()
        context = AgentStatus(identity=self.identity,
                              platform=self.platform,
                              exit_code=obj['exit_code'],
                              priority=obj['priority'],
                              running=obj['running'],
                              tag=obj['tag'],
                              uuid=obj['uuid'])

        return context

    @property
    def rpc(self) -> AgentRPC:
        return self.configs.rpc


@dataclass
class AgentStatus:
    identity: str
    platform: str
    uuid: str
    pid: Optional[str] = None
    running: bool = False
    tag: Optional[str] = ''
    exit_code: Optional[str] = None
    priority: Optional[str] = None


class Historian:
    pass


class Driver:
    pass


def cbool(data: str) -> bool:
    if data.lower() == 'true':
        status = True
    elif data.lower() == 'false':
        status = False
    else:
        status = False
    return status


def get_link(key: str, links: List[Link]) -> Link:
    for link in links:
        if link.key == key:
            return link
    return None


@dataclass
class Configs(Http):
    identity: str
    links: List[Link]

    def __get_link__(self, key) -> Optional[Link]:
        for link in self.links:
            if link.key == key:
                return link
        return None

    @property
    def running(self) -> bool:
        response = self.get(self.__get_link__('enabled').link)
        return cbool(response.json()['status'])

    @property
    def rpc(self) -> AgentRPC:
        response = self.get(self.__get_link__('rpc').link)
        rpc: Optional[AgentRPC] = None
        if response.ok:
            links = build_links(response.json()[LINK_IDENTIFIER])
            rpc = AgentRPC(links)

        return rpc

    @property
    def status(self):
        response = self.get(self.__get_link__('enabled').link)
        return response.json()

    @property
    def enabled(self) -> AgentEnabled:
        response = self.get(self.__get_link__('enabled').link)
        status = response.json()['status']
        if status.lower() == 'true':
            status = True
        elif status.lower() == 'false':
            status = False
        priority = response.json()['priority']
        if priority == 'None':
            priority = None
        else:
            priority = int(priority)
        return AgentEnabled(enabled=bool(status), priority=priority)

    def set_enabled(self, enabled: bool, priority: int = 50):
        if enabled:
            response = self.put(self.__get_link__('enabled').link, params={'priority': priority})
        else:
            response = self.delete(self.__get_link__('enabled').link)

    def set_priority(self, priority: int):
        self.set_enabled(True, priority)


class ConfigStoreEntry(Http):
    link: Optional[Link] = None
    content: Optional[str] = None
    content_type: Optional[str] = None


@dataclass
class AgentEnabled:
    enabled: bool
    priority: Optional[int] = 0


@dataclass
class AgentRPC(Http):
    links: List[Link]

    def execute(self, function_name: str, **kwargs) -> RPCResponse:
        link = get_link(function_name, self.links)
        if link is None:
            raise InvalidRPCFunction(f"{function_name}")

        body = {}
        for k, v in kwargs.items():
            body[k] = v
        response = self.post(url=link.link, json=body)

        rpc_repsonse: Optional[RPCResponse] = None
        if response.ok:
            rpc_repsonse = RPCResponse(data=response.json())

        return rpc_repsonse


@dataclass
class RPCResponse:
    data: Any
    error: Optional[bool] = False
