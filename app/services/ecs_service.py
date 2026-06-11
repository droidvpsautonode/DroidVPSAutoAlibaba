"""
ECS Service module.
Wraps all Alibaba Cloud ECS API calls used by the bot.
"""

import asyncio
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from alibabacloud_ecs20140526 import models as ecs_models
from alibabacloud_tea_util.models import RuntimeOptions

from app.services.aliyun_client import create_ecs_client

# Thread pool for running synchronous SDK calls
_executor = ThreadPoolExecutor(max_workers=10)


def _run_sync(func, *args, **kwargs):
    """Helper to run synchronous function."""
    return func(*args, **kwargs)


async def run_in_executor(func, *args, **kwargs):
    """Run a synchronous function in a thread pool executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _executor, lambda: func(*args, **kwargs)
    )


class ECSService:
    """Service class for Alibaba Cloud ECS operations."""

    def __init__(self, access_key_id: str, access_key_secret: str):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret

    def _get_client(self, region_id: str = "cn-hangzhou"):
        """Get ECS client for a specific region."""
        return create_ecs_client(
            self.access_key_id,
            self.access_key_secret,
            region_id
        )

    # ==================== REGIONS ====================

    async def describe_regions(self) -> list[dict]:
        """
        Get all available ECS regions.
        Returns list of {"region_id": str, "region_name": str}
        """
        def _call():
            client = self._get_client()
            request = ecs_models.DescribeRegionsRequest(
                accept_language="en-US"
            )
            response = client.describe_regions_with_options(
                request, RuntimeOptions()
            )
            regions = []
            if response.body and response.body.regions and response.body.regions.region:
                for r in response.body.regions.region:
                    regions.append({
                        "region_id": r.region_id,
                        "region_name": r.local_name or r.region_id,
                    })
            return regions

        return await run_in_executor(_call)

    async def scan_regions_with_instances(self) -> list[dict]:
        """
        Scan all regions and return only those with ECS instances.
        Returns list of {"region_id", "region_name", "instance_count"}
        """
        active_regions, _ = await self.scan_regions_detailed()
        return active_regions

    async def scan_regions_detailed(self) -> tuple[list[dict], list[str]]:
        """
        Scan all regions for ECS instances.
        Returns (active_regions, errors).
        - active_regions: list of {"region_id", "region_name", "instance_count"}
        - errors: list of human-readable error strings per region that failed.

        Uses limited concurrency (batch) to avoid Alibaba Cloud throttling,
        and does NOT silently swallow errors.
        """
        regions = await self.describe_regions()
        active_regions: list[dict] = []
        errors: list[str] = []

        async def check_region(region: dict):
            region_id = region["region_id"]
            region_name = region["region_name"]
            try:
                count = await self.count_instances(region_id)
                if count > 0:
                    return ("ok", {
                        "region_id": region_id,
                        "region_name": region_name,
                        "instance_count": count,
                    })
                return ("empty", None)
            except Exception as e:
                msg = self._parse_error(e)
                return ("error", f"{region_name} ({region_id}): {msg}")

        # Process in batches of 5 to avoid throttling (Throttling errors)
        batch_size = 5
        for i in range(0, len(regions), batch_size):
            batch = regions[i:i + batch_size]
            results = await asyncio.gather(
                *[check_region(r) for r in batch],
                return_exceptions=True
            )
            for result in results:
                if isinstance(result, Exception):
                    errors.append(str(result))
                    continue
                status, payload = result
                if status == "ok" and payload:
                    active_regions.append(payload)
                elif status == "error" and payload:
                    errors.append(payload)

        return active_regions, errors

    async def count_instances(self, region_id: str) -> int:
        """Count instances in a region."""
        def _call():
            client = self._get_client(region_id)
            request = ecs_models.DescribeInstancesRequest(
                region_id=region_id,
                page_size=10,
                page_number=1,
            )
            response = client.describe_instances_with_options(
                request, RuntimeOptions()
            )
            return response.body.total_count or 0

        return await run_in_executor(_call)

    # ==================== INSTANCES ====================

    async def describe_instances(self, region_id: str) -> list[dict]:
        """
        Get all instances in a region.
        Returns list of instance dicts.
        """
        def _call():
            client = self._get_client(region_id)
            request = ecs_models.DescribeInstancesRequest(
                region_id=region_id,
                page_size=100,
                page_number=1,
            )
            response = client.describe_instances_with_options(
                request, RuntimeOptions()
            )
            instances = []
            if response.body and response.body.instances and response.body.instances.instance:
                for inst in response.body.instances.instance:
                    # Get public IP
                    public_ips = []
                    if inst.public_ip_address and inst.public_ip_address.ip_address:
                        public_ips = inst.public_ip_address.ip_address
                    if inst.eip_address and inst.eip_address.ip_address:
                        public_ips.append(inst.eip_address.ip_address)

                    # Get private IP
                    private_ips = []
                    if inst.vpc_attributes and inst.vpc_attributes.private_ip_address:
                        if inst.vpc_attributes.private_ip_address.ip_address:
                            private_ips = inst.vpc_attributes.private_ip_address.ip_address
                    if inst.inner_ip_address and inst.inner_ip_address.ip_address:
                        private_ips.extend(inst.inner_ip_address.ip_address)

                    # Get security groups
                    sg_ids = []
                    if inst.security_group_ids and inst.security_group_ids.security_group_id:
                        sg_ids = inst.security_group_ids.security_group_id

                    instances.append({
                        "instance_id": inst.instance_id,
                        "instance_name": inst.instance_name or inst.instance_id,
                        "status": inst.status,
                        "os_name": inst.osname or "",
                        "os_type": inst.ostype or "",
                        "cpu": inst.cpu,
                        "memory": inst.memory,  # in MB
                        "instance_type": inst.instance_type or "",
                        "public_ips": public_ips,
                        "private_ips": private_ips,
                        "security_group_ids": sg_ids,
                        "region_id": inst.region_id,
                        "expired_time": inst.expired_time or "",
                        "creation_time": inst.creation_time or "",
                        "image_id": inst.image_id or "",
                    })
            return instances

        return await run_in_executor(_call)

    async def describe_instance(self, region_id: str, instance_id: str) -> Optional[dict]:
        """Get a single instance detail."""
        instances = await self.describe_instances(region_id)
        for inst in instances:
            if inst["instance_id"] == instance_id:
                return inst
        return None

    # ==================== INSTANCE ACTIONS ====================

    async def reboot_instance(self, region_id: str, instance_id: str, force: bool = False) -> str:
        """Reboot an instance. Returns success message or raises."""
        def _call():
            client = self._get_client(region_id)
            request = ecs_models.RebootInstanceRequest(
                instance_id=instance_id,
                force_stop=force,
            )
            client.reboot_instance_with_options(request, RuntimeOptions())
            return "Perintah reboot berhasil dikirim."

        return await run_in_executor(_call)

    async def start_instance(self, region_id: str, instance_id: str) -> str:
        """Start an instance."""
        def _call():
            client = self._get_client(region_id)
            request = ecs_models.StartInstanceRequest(
                instance_id=instance_id,
            )
            client.start_instance_with_options(request, RuntimeOptions())
            return "Perintah start berhasil dikirim."

        return await run_in_executor(_call)

    async def stop_instance(self, region_id: str, instance_id: str, force: bool = False) -> str:
        """Stop an instance."""
        def _call():
            client = self._get_client(region_id)
            request = ecs_models.StopInstanceRequest(
                instance_id=instance_id,
                force_stop=force,
            )
            client.stop_instance_with_options(request, RuntimeOptions())
            return "Perintah shutdown berhasil dikirim."

        return await run_in_executor(_call)

    async def delete_instance(self, region_id: str, instance_id: str, force: bool = True) -> str:
        """Delete an instance."""
        def _call():
            client = self._get_client(region_id)
            request = ecs_models.DeleteInstanceRequest(
                instance_id=instance_id,
                force=force,
            )
            client.delete_instance_with_options(request, RuntimeOptions())
            return "Instance berhasil dihapus."

        return await run_in_executor(_call)

    async def reset_password(self, region_id: str, instance_id: str, password: str) -> str:
        """Reset instance password using ModifyInstanceAttribute."""
        def _call():
            client = self._get_client(region_id)
            request = ecs_models.ModifyInstanceAttributeRequest(
                instance_id=instance_id,
                password=password,
            )
            client.modify_instance_attribute_with_options(request, RuntimeOptions())
            return (
                "Password berhasil direset.\n"
                "⚠️ Beberapa OS memerlukan reboot agar password baru aktif."
            )

        return await run_in_executor(_call)

    async def replace_system_disk(
        self,
        region_id: str,
        instance_id: str,
        image_id: str,
        password: str
    ) -> str:
        """
        Replace system disk (reinstall OS).
        Instance must be in Stopped state.
        """
        def _call():
            client = self._get_client(region_id)
            request = ecs_models.ReplaceSystemDiskRequest(
                instance_id=instance_id,
                image_id=image_id,
                password=password,
            )
            client.replace_system_disk_with_options(request, RuntimeOptions())
            return (
                "System disk berhasil diganti.\n"
                "OS baru sedang diinstal. Tunggu beberapa menit."
            )

        return await run_in_executor(_call)

    # ==================== SECURITY GROUP ====================

    async def authorize_security_group(
        self,
        region_id: str,
        security_group_id: str,
        ip_protocol: str,
        port_range: str = "1/65535",
        source_cidr_ip: str = "0.0.0.0/0",
        priority: int = 1,
    ) -> str:
        """
        Add an inbound rule to a security group.
        ip_protocol: TCP, UDP, ICMP, GRE, ALL
        """
        def _call():
            client = self._get_client(region_id)
            request = ecs_models.AuthorizeSecurityGroupRequest(
                region_id=region_id,
                security_group_id=security_group_id,
                permissions=[
                    ecs_models.AuthorizeSecurityGroupRequestPermissions(
                        ip_protocol=ip_protocol,
                        port_range=port_range,
                        source_cidr_ip=source_cidr_ip,
                        policy="accept",
                        priority=str(priority),
                        nic_type="intranet",
                        description=f"Bot: Open {ip_protocol} {port_range}",
                    )
                ]
            )
            client.authorize_security_group_with_options(request, RuntimeOptions())
            return f"Rule {ip_protocol} {port_range} berhasil ditambahkan."

        return await run_in_executor(_call)

    async def revoke_security_group(
        self,
        region_id: str,
        security_group_id: str,
        ip_protocol: str,
        port_range: str = "1/65535",
        source_cidr_ip: str = "0.0.0.0/0",
        priority: int = 1,
    ) -> str:
        """
        Revoke (remove) an inbound rule from a security group.
        """
        def _call():
            client = self._get_client(region_id)
            request = ecs_models.RevokeSecurityGroupRequest(
                region_id=region_id,
                security_group_id=security_group_id,
                permissions=[
                    ecs_models.RevokeSecurityGroupRequestPermissions(
                        ip_protocol=ip_protocol,
                        port_range=port_range,
                        source_cidr_ip=source_cidr_ip,
                        policy="accept",
                        priority=str(priority),
                        nic_type="intranet",
                    )
                ]
            )
            client.revoke_security_group_with_options(request, RuntimeOptions())
            return f"Rule {ip_protocol} {port_range} berhasil dihapus."

        return await run_in_executor(_call)

    async def open_all_tcp(self, region_id: str, security_group_id: str) -> str:
        """Open all TCP ports (1-65535) to 0.0.0.0/0."""
        return await self.authorize_security_group(
            region_id=region_id,
            security_group_id=security_group_id,
            ip_protocol="TCP",
            port_range="1/65535",
        )

    async def open_all_udp(self, region_id: str, security_group_id: str) -> str:
        """Open all UDP ports (1-65535) to 0.0.0.0/0."""
        return await self.authorize_security_group(
            region_id=region_id,
            security_group_id=security_group_id,
            ip_protocol="UDP",
            port_range="1/65535",
        )

    async def open_all_tcp_udp(self, region_id: str, security_group_id: str) -> str:
        """Open all TCP and UDP ports (1-65535) to 0.0.0.0/0."""
        results = []
        try:
            tcp_result = await self.open_all_tcp(region_id, security_group_id)
            results.append(f"TCP: {tcp_result}")
        except Exception as e:
            error_msg = self._parse_error(e)
            if "already exists" in error_msg.lower() or "AuthorizationRuleExists" in str(e):
                results.append("TCP: Rule sudah ada, dilewati.")
            else:
                results.append(f"TCP: Gagal - {error_msg}")

        try:
            udp_result = await self.open_all_udp(region_id, security_group_id)
            results.append(f"UDP: {udp_result}")
        except Exception as e:
            error_msg = self._parse_error(e)
            if "already exists" in error_msg.lower() or "AuthorizationRuleExists" in str(e):
                results.append("UDP: Rule sudah ada, dilewati.")
            else:
                results.append(f"UDP: Gagal - {error_msg}")

        return "\n".join(results)

    async def revoke_all_tcp(self, region_id: str, security_group_id: str) -> str:
        """Revoke all TCP ports rule."""
        return await self.revoke_security_group(
            region_id=region_id,
            security_group_id=security_group_id,
            ip_protocol="TCP",
            port_range="1/65535",
        )

    async def revoke_all_udp(self, region_id: str, security_group_id: str) -> str:
        """Revoke all UDP ports rule."""
        return await self.revoke_security_group(
            region_id=region_id,
            security_group_id=security_group_id,
            ip_protocol="UDP",
            port_range="1/65535",
        )

    async def revoke_all_tcp_udp(self, region_id: str, security_group_id: str) -> str:
        """Revoke all TCP and UDP ports rule."""
        results = []
        try:
            tcp_result = await self.revoke_all_tcp(region_id, security_group_id)
            results.append(f"TCP: {tcp_result}")
        except Exception as e:
            error_msg = self._parse_error(e)
            results.append(f"TCP: Gagal - {error_msg}")

        try:
            udp_result = await self.revoke_all_udp(region_id, security_group_id)
            results.append(f"UDP: {udp_result}")
        except Exception as e:
            error_msg = self._parse_error(e)
            results.append(f"UDP: Gagal - {error_msg}")

        return "\n".join(results)

    # ==================== ERROR HANDLING ====================

    @staticmethod
    def _parse_error(exception: Exception) -> str:
        """Parse Alibaba Cloud API error into readable message."""
        error_str = str(exception)

        # Common error translations
        error_map = {
            "InvalidAccessKeyId": "AccessKey ID tidak valid.",
            "SignatureDoesNotMatch": "AccessKey Secret tidak cocok.",
            "Forbidden": "Akses ditolak. Periksa permission RAM user.",
            "InvalidInstanceId.NotFound": "Instance tidak ditemukan.",
            "IncorrectInstanceStatus": "Status instance tidak sesuai untuk aksi ini.",
            "InvalidSecurityGroupId.NotFound": "Security group tidak ditemukan.",
            "AuthorizationRuleExists": "Rule security group sudah ada.",
            "Throttling": "Terlalu banyak request. Coba lagi nanti.",
            "InvalidPassword": "Format password tidak valid.",
            "InvalidImageId.NotFound": "Image ID tidak ditemukan.",
            "OperationDenied": "Operasi ditolak oleh sistem.",
            "InternalError": "Error internal Alibaba Cloud. Coba lagi nanti.",
        }

        for key, message in error_map.items():
            if key in error_str:
                return message

        # Fallback: return truncated error
        if len(error_str) > 200:
            return error_str[:200] + "..."
        return error_str
