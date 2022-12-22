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

def rg_create(name, location):
    rg_result = resource_client.resource_groups.create_or_update(
        name, {"location": location})
    print(f"Provisioned resource group {rg_result.name}")

def vnet_create(name, rg, location, address_space):
    poller = network_client.virtual_networks.begin_create_or_update(
        rg, name, {
            "location": location,
            "address_space": {"address_prefixes": [address_space]}})
    vnet_result = poller.result()
    print(f"Provisioned virtual network {vnet_result.name}")

def subnet_create(name, rg, vnet, prefix):
    poller = network_client.subnets.begin_create_or_update(
    rg, vnet, name,
        {"address_prefix": prefix})
    subnet_result = poller.result()
    print(f"Provisioned virtual subnet {subnet_result.name}")
    return subnet_result.id

def publicip_create(name, rg, location):
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

def interface_create(name, config_name, rg, location, subnet_id, publicip_id):
    poller = network_client.network_interfaces.begin_create_or_update(
        rg, name, {
            "location": location,
            "ip_configurations": [
                {
                    "name": config_name,
                    "subnet": {"id": subnet_id},
                    "public_ip_address": {"id": publicip_id},
                }
            ],
        },
    )
    nic_result = poller.result()
    print(f"Provisioned network interface client {nic_result.name}")
    return nic_result.id

def vm_create(name, rg, location, nic_id):
    print(f"Provisioning virtual machine {name}")
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

def vnet_peering_create(name, rg, vnet, target_rg, target_vnet):
    remote_vnet = "/subscriptions/" + SUBSCRIPTION_ID + "/resourceGroups/" + target_rg + "/providers/Microsoft.Network/virtualNetworks/" + target_vnet + ""
    virtual_network_peering = network_client.virtual_network_peerings.begin_create_or_update(
    rg, vnet, name, {
        "allow_virtual_network_access": True,
        "allow_forwarded_traffic": True,
        "allow_gateway_transit": False,
        "use_remote_gateways": False,
        "remote_virtual_network": {
            "id": remote_vnet,
        }
    }).result()
    print("Create virtual network peering:\n{}".format(virtual_network_peering))

    # Get virtual network peering
    virtual_network_peering = network_client.virtual_network_peerings.get(
    rg, vnet, name)
    print("Get virtual network peering:\n{}".format(virtual_network_peering))

#Microsoft.Network/virtualHubs/ipConfigurations
def create_routeserver(name, rg, location, vnet):
    publicip_id = publicip_create(name+"pubIP", rg, location)
    subnet_id = subnet_create("RouteServerSubnet", rg, vnet, "10.1.1.0/24")
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
    print("Create Route Server:\n{}".format(virtual_hub))
    return virtual_hub.id

def main():
    RESOURCE_GROUP = "mazdak-rg"
    LOCATION = "eastus2"
    VNET_NAME = "remote-vnet"
    AKS_RESOURCE_GROUP = "MC_mazdak-bz-rg_mazdak-bz-rg_eastus2"
    AKS_VNET_NAME = "aks-vnet-31584722"
    IP_NAME = "mazdak-vm-ip"
    IP_CONFIG_NAME = "mazdak-vm-ip-config"
    NIC_NAME = "mazdak-vm-nic"
    VM_NAME = "mazdak-vm"
    VNET_PEERING = "mazdak-peering1"
    VNET_PEERING1 = "mazdak-peering2"

    rg_create(RESOURCE_GROUP, LOCATION)
    vnet_create(VNET_NAME, RESOURCE_GROUP, LOCATION, "10.1.0.0/16")
    subnet_id = subnet_create("default", RESOURCE_GROUP, VNET_NAME, "10.1.0.0/24")
    #publicip_id = publicip_create(IP_NAME, RESOURCE_GROUP, LOCATION)
    #nic_id = interface_create(NIC_NAME, IP_CONFIG_NAME, RESOURCE_GROUP, LOCATION, subnet_id, publicip_id)
    #vm_create(VM_NAME, RESOURCE_GROUP, LOCATION, nic_id)
    #vnet_peering_create(VNET_PEERING, RESOURCE_GROUP, VNET_NAME, AKS_RESOURCE_GROUP, AKS_VNET_NAME)
    create_routeserver("mazdak-ars", RESOURCE_GROUP, LOCATION, VNET_NAME)


if __name__ == "__main__":
    main()
