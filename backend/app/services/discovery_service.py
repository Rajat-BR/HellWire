import socket
from zeroconf import IPVersion, ServiceInfo
from zeroconf.asyncio import AsyncZeroconf

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


class HellWireAdvertiser:
    def __init__(self, port: int = 8000, device_name: str | None = None):
        self.port = port
        self.device_name = device_name or socket.gethostname()
        self.aiozc: AsyncZeroconf | None = None
        self.service_info: ServiceInfo | None = None

    async def start(self):
        # Register and broadcast the _hellwire._tcp service.
        local_ip = get_local_ip()
        ip_bytes = socket.inet_aton(local_ip)

        # Service instance name must end with service type
        instance_name = f"{self.device_name}.{SERVICE_TYPE}"

        # Text Record: metadata shared with other peers
        properties = {
            "version": "1.0.0",
            "alias": self.device_name,
            "device_model": "Python Backend",
        }

        self.service_info = ServiceInfo(
            type_=SERVICE_TYPE,
            name=instance_name,
            addresses=[ip_bytes],
            port=self.port,
            properties=properties,
            server=f"{self.device_name}.local.",
        )

        # Use AsyncZeroconf and await registration
        self.aiozc = AsyncZeroconf(ip_version=IPVersion.V4Only)
        await self.aiozc.async_register_service(self.service_info)
        print(f"[mDNS] Registered {instance_name} on {local_ip}:{self.port}")

    async def stop(self):
        if self.aiozc and self.service_info:
            print(f"[mDNS] Unregistering {self.service_info.name}...")
            await self.aiozc.async_unregister_service(self.service_info)
            await self.aiozc.async_close()
            self.service_info = None
            self.aiozc = None
            print("[mDNS] Service successfully unregistered")