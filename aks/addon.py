import os

from azure.identity import AzureCliCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient

SUBSCRIPTION_ID = os.environ.get("SUBSCRIPTION_ID", None)
credential = AzureCliCredential()
resource_client = ResourceManagementClient(credential, SUBSCRIPTION_ID)
compute_client = ComputeManagementClient(credential, SUBSCRIPTION_ID)
network_client = NetworkManagementClient(credential, SUBSCRIPTION_ID)

def create_rg(name, location):
    rg_result = resource_client.resource_groups.create_or_update(
        name, {"location": location})
    print(f"Provisioned resource group {rg_result.name}")

def create_vnet(name, rg, location, address_space):
    poller = network_client.virtual_networks.begin_create_or_update(
        rg, name, {
            "location": location,
            "address_space": {"address_prefixes": [address_space]}})
    vnet_result = poller.result()
    print(f"Provisioned virtual network {vnet_result.name}")

def create_subnet(name, rg, vnet, prefix):
    poller = network_client.subnets.begin_create_or_update(
    rg, vnet, name,
        {"address_prefix": prefix})
    subnet_result = poller.result()
    print(f"Provisioned virtual subnet {subnet_result.name}")
    return subnet_result.id

def create_publicip(name, rg, location):
    poller = network_client.public_ip_addresses.begin_create_or_update(
    rg, name, {
        "location": location,
        "sku": {"name": "Standard"},
        "public_ip_allocation_method": "Static",
        "public_ip_address_version": "IPV4",
    })
    ip_address_result = poller.result()
    print(f"Provisioned public IP {ip_address_result.name} {ip_address_result.ip_address}")
    return ip_address_result.id

def create_interface(name, rg, location, subnet_id, publicip_id, nsg_id):
    poller = network_client.network_interfaces.begin_create_or_update(
        rg, name, {
            "location": location,
            "ip_configurations": [
                {
                    "name": name+"ipconfig",
                    "subnet": {"id": subnet_id},
                    "public_ip_address": {"id": publicip_id},
                }
            ],
            "network_security_group": {
                "id": nsg_id,
            },
        },
    )
    nic_result = poller.result()
    print(f"Provisioned network interface client {nic_result.name}")
    return nic_result.id

def create_nsg(name, rg, location):
    nsg = network_client.network_security_groups.begin_create_or_update(
    rg, name, {
        "location": location,
        "security_rules": [
            {
                "name": "allow-ssh",
                "protocol": "Tcp",
                "destination_port_range": "22",
                "source_port_range": "*",
                "source_address_prefix": "*",
                "destination_address_prefix": "*",
                "access": "Allow",
                "direction": "Inbound",
                "priority": 100,
            },
        ],
    }).result()
    print(f"Provisioned network security group {nsg.name}")
    return nsg.id

def create_vm(name, rg, location, subnet_id):
    print(f"Provisioning virtual machine {name}")
    publicip_id = create_publicip(name+"pubip", rg, location)
    nsg_id = create_nsg(name+"-nsg", rg, location)
    nic_id = create_interface(name+"nic", rg, location, subnet_id, publicip_id, nsg_id)
    poller = compute_client.virtual_machines.begin_create_or_update(
    rg, name, {
        "location": location,
        "storage_profile": {
            "image_reference": {
                "publisher": "Canonical",
                "offer": "0001-com-ubuntu-server-jammy",
                "sku": "22_04-lts-gen2",
                "version": "latest",
            }
        },
        "hardware_profile": {"vm_size": "Standard_DS1_v2"},
        "os_profile": {
            "computer_name": name,
            "admin_username": "mazdak",
            "admin_password": "ChangePa$$w0rd24",
        },
        "network_profile": {
            "network_interfaces": [
                {
                    "id": nic_id,
                }
            ]
        },
    })
    vm_result = poller.result()
    print(f"Provisioned virtual machine {vm_result.name}")

def create_vnet_peering(name, rg, vnet, target_rg, target_vnet, local_gw, remote_gw):
    remote_vnet = "/subscriptions/" + SUBSCRIPTION_ID + "/resourceGroups/" + target_rg + "/providers/Microsoft.Network/virtualNetworks/" + target_vnet + ""
    virtual_network_peering = network_client.virtual_network_peerings.begin_create_or_update(
    rg, vnet, name, {
        "allow_virtual_network_access": True,
        "allow_forwarded_traffic": True,
        "allow_gateway_transit": local_gw,
        "use_remote_gateways": remote_gw,
        "remote_virtual_network": {
            "id": remote_vnet,
        }
    }).result()
    print("Create virtual network peering:\n{}".format(virtual_network_peering))

    # Get virtual network peering
    virtual_network_peering = network_client.virtual_network_peerings.get(
    rg, vnet, name)
    print("Get virtual network peering:\n{}".format(virtual_network_peering))

def create_routeserver(name, rg, location, vnet):
    publicip_id = create_publicip(name+"pubIP", rg, location)
    subnet_id = create_subnet("RouteServerSubnet", rg, vnet, "10.225.0.0/24")
    virtual_hub = network_client.virtual_hubs.begin_create_or_update(
    rg, name, {
        "location": location,
        "properties": {
            "sku": "Standard",
        },
        "ip_configurations": [
            {
                "name": name+"ipconfig",
                "subnet": {"id": subnet_id},
                "public_ip_address": {"id": publicip_id},
            }
        ],
    }).result()

    ip_config = network_client.virtual_hub_ip_configuration.begin_create_or_update(
    rg, name, name+"ipConfig", {
        "name": name+"ipconfig", 
        "subnet": {"id": subnet_id},
        "public_ip_address": {"id": publicip_id},
    }).result()
    print("Create Route Server:\n{}".format(virtual_hub))
    return virtual_hub.id

def create_peer(hub, name, rg, location, ip, asn):
    peer = network_client.virtual_hub_bgp_connection.begin_create_or_update(
        rg, hub, name, {
            "peer_asn": asn,
            "peer_ip": ip,
    }).result()
    print("Created BGP peer:\n{}".format(peer))

def main():
    RESOURCE_GROUP = "mazdak-rg"
    LOCATION = "eastus2"
    VNET_NAME = "remote-vnet"
    AKS_RG = "MC_mazdak-bz-lsl5_mazdak-bz-lsl5_eastus2"
    AKS_VNET = "aks-vnet-14128042"

    create_rg(RESOURCE_GROUP, LOCATION)
    create_vnet(VNET_NAME, RESOURCE_GROUP, LOCATION, "10.1.0.0/16")
    subnet_id = create_subnet("default", RESOURCE_GROUP, VNET_NAME, "10.1.0.0/24")
    create_vm("mazdak-vm", RESOURCE_GROUP, LOCATION, subnet_id)

    create_routeserver("mazdak-ars", AKS_RG, LOCATION, AKS_VNET)
    create_peer("mazdak-ars", "peer1", AKS_RG, LOCATION, "10.224.0.4", 64512)
    create_vnet_peering("aks-remote", AKS_RG, AKS_VNET, RESOURCE_GROUP, VNET_NAME, True, False)
    create_vnet_peering("remote-aks", RESOURCE_GROUP, VNET_NAME, AKS_RG, AKS_VNET, False, True)

if __name__ == "__main__":
    main()
