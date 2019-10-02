from os import environ
import requests
import json
from ec2_utils.utils import contains_key, get_file_content

def get_private_ip():
    metadata = requests.get(environ["ECS_CONTAINER_METADATA_URI"]).json()
    if not metadata:
        return None
                        
    if contains_key(metadata, "Networks"):
        first_network = metadata["Networks"][0]
        if first_network["NetworkMode"] == "host":
            metadata = json.loads(get_file_content(environ["ECS_CONTAINER_METADATA_FILE"]))
            return metadata["HostPrivateIPv4Address"]
        elif first_network["NetworkMode"] == "awsvpc":
            return first_network["IPv4Addresses"][0]
