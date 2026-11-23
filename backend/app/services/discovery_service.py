import asyncio
import socket
import time
from dataclasses import asdict, dataclass
from zeroconf import IPVersion, ServiceInfo, ServiceStateChange
from zeroconf.asyncio import AsyncZeroconf, AsyncServiceBrowser, AsyncServiceInfo

SERVICE_TYPE = "_hellwire._tcp.local."


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()

@dataclass
class Peer:
    instance_name: str
    alias: str
    device_model: str
    version: str
    ip: str
    port: int
    last_seen: float

    def to_dict(self) -> dict:
        return asdict(self)



class PeerRegistery:
    # in-Memory store for active LAN peers
    def __init__(self):
        self._peers: dict[str, Peer] = {}

    def upsert(self, peer: Peer) -> None:
        self._peers[peer.instance_name] = peer

    def remove(self, instance_name: str) -> Peer | None:
        return self._peers.pop(instance_name, None)

    def list_peers(self) -> list[dict]:
        return [peer.to_dict() for peer in self._peers.values()]
    


class HellWireAdvertiser:
    def __init__(self, port: int = 8000, device_name: str | None = None):
        self.port = port
        self.device_name = device_name or socket.gethostname()
        self.instance_name = f"{self.device_name}.{SERVICE_TYPE}"
        self.aiozc: AsyncZeroconf | None = None
        self.service_info: ServiceInfo | None = None

    async def start(self, aiozc: AsyncZeroconf | None = None):
        # Register and broadcast the _hellwire._tcp service.
        local_ip = get_local_ip()
        ip_bytes = socket.inet_aton(local_ip)


        # Text Record: metadata shared with other peers
        properties = {
            "version": "1.0.0",
            "alias": self.device_name,
            "device_model": "Python Backend",
        }

        self.service_info = ServiceInfo(
            type_=SERVICE_TYPE,
            name=self.instance_name,
            addresses=[ip_bytes],
            port=self.port,
            properties=properties,
            server=f"{self.device_name}.local.",
        )

        # Use AsyncZeroconf and await registration
        self.aiozc = aiozc or AsyncZeroconf(ip_version=IPVersion.V4Only)
        await self.aiozc.async_register_service(self.service_info)
        print(f"[mDNS] Registered {self.instance_name} on {local_ip}:{self.port}")

    async def stop(self, close_aiozc: bool = True):
        if self.aiozc and self.service_info:
            print(f"[mDNS] Unregistering {self.service_info.name}...")
            await self.aiozc.async_unregister_service(self.service_info)
            if close_aiozc:
                await self.aiozc.async_close()
            self.service_info = None
            if close_aiozc:
                self.aiozc = None
            print("[mDNS] Service successfully unregistered")


class HellWireBrowser:
    # Listens for _hellwire._tcp.local. peers using AsyncServiceBrowser

    def __init__(
            self,
            registry: PeerRegistery,
            ignore_instance_name: str | None = None,
    ):
        self.registry = registry
        self.ignore_instance_name = ignore_instance_name
        self.aiozc: AsyncZeroconf | None = None
        self.browser: AsyncServiceBrowser | None = None
        self._tasks: set[asyncio.Task] = set()


    def _on_state_change(
            self,
            zeroconf,
            service_type: str,
            name: str,
            state_change: ServiceStateChange,
    ) -> None:
        if self.ignore_instance_name and name == self.ignore_instance_name:
            return 

        if state_change in (ServiceStateChange.Added, ServiceStateChange.Updated):
            task = asyncio.create_task(self._resolve_and_store(service_type, name))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

        elif state_change == ServiceStateChange.Removed:
            removed = self.registry.remove(name)
            if removed:
                print(f"[mDNS] Peer left: {removed.alias} ({removed.ip}:{removed.port})")


    async def _resolve_and_store(self, service_type: str, name: str) -> None:
        if not self.aiozc:
            return

        info = AsyncServiceInfo(service_type, name)
        found = await info.async_request(self.aiozc.zeroconf, timeout=3000)
        if not found:
            return 

        ipv4_addrs = info.parsed_addresses(IPVersion.V4Only)
        if not ipv4_addrs or info.port is None:
            return

        raw_props = info.properties or {}
        decoded_props = {
            (k.decode("utf-8", errors="ignore") if isinstance(k, bytes) else str(k)):
            (v.decode("utf-8", errors="ignore") if isinstance(v, bytes) else str(v))
            for k, v in raw_props.items()
        }

        alias = decoded_props.get("alias") or name.split(".")[0]
        peer = Peer(
            instance_name=name,
            alias=alias,
            device_model=decoded_props.get("device_model", "Unknown"),
            version=decoded_props.get("version", "Unknown"),
            ip=ipv4_addrs[0],
            port=info.port,
            last_seen=time.time(),
        )

        self.registry.upsert(peer)
        print(f"[mDNS] Peer active: {peer.alias} ({peer.ip}:{peer.port})")

    async def start(self, aiozc: AsyncZeroconf | None = None) -> None:
        self.aiozc = aiozc or AsyncZeroconf(ip_version=IPVersion.V4Only)
        self.browser = AsyncServiceBrowser(
            self.aiozc.zeroconf,
            SERVICE_TYPE,
            handlers=[self._on_state_change],
        )
        print(f"[mDNS] Browsing for {SERVICE_TYPE}")

    async def stop(self, close_aiozc: bool = True) -> None:
        for task in list(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        if self.browser:
            await self.browser.async_cancel()
            self.browser = None

        if close_aiozc and self.aiozc:
            await self.aiozc.async_close()
            self.aiozc = None
