"""
Alibaba Cloud Client Factory.
Creates authenticated ECS client instances for a given account.
"""

from alibabacloud_ecs20140526.client import Client as EcsClient
from alibabacloud_tea_openapi.models import Config as OpenApiConfig


def create_ecs_client(
    access_key_id: str,
    access_key_secret: str,
    region_id: str = "cn-hangzhou"
) -> EcsClient:
    """
    Create an Alibaba Cloud ECS client for the given credentials and region.
    
    Args:
        access_key_id: Alibaba Cloud AccessKey ID
        access_key_secret: Alibaba Cloud AccessKey Secret
        region_id: Region ID (default cn-hangzhou for initial API calls)
    
    Returns:
        EcsClient instance
    """
    config = OpenApiConfig(
        access_key_id=access_key_id,
        access_key_secret=access_key_secret,
        region_id=region_id,
        endpoint=f"ecs.{region_id}.aliyuncs.com"
    )
    return EcsClient(config)
