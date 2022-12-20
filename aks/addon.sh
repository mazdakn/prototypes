#!/bin/bash

REMOTE_RG="mazdak-bz-rg"
AKS_RG="MC_mazdak-bz-rg_mazdak-bz-rg_eastus2"
AKS_VNET="aks-vnet-31584722"

az network vnet subnet create -n RouteServerSubnet -g $AKS_RG --vnet-name $AKS_VNET --address-prefix 10.225.0.0/24
SUBNET_ID=$(az network vnet subnet show --name RouteServerSubnet --resource-group $AKS_RG --vnet-name $AKS_VNET --query id -o tsv)
az network public-ip create --name RouteServerIP -g $REMOTE_RG --version IPv4 --sku Standard
az network routeserver create -n myRouteServer -g $REMOTE_RG --hosted-subnet $SUBNET_ID --public-ip-address RouteServerIP
az network routeserver peering create --name RR1 --peer-ip 10.224.0.4 --peer-asn 64512 --routeserver myRouteServer -g $REMOTE_RG

az network vnet create --name myVNet --resource-group $REMOTE_RG --address-prefixes 10.0.0.0/16 --subnet-name Subnet1 --subnet-prefix 10.0.0.0/24
# Get the id for myVirtualNetwork1.
RemotevNetId=$(az network vnet show --resource-group $REMOTE_RG --name myVNet --query id --out tsv)
# Get the id for myVirtualNetwork2.
AKSvNetId=$(az network vnet show --resource-group $AKS_RG --name $AKS_VNET --query id --out tsv)

az network vnet peering create --name  aks-remote --resource-group $AKS_RG --vnet-name $AKS_VNET --remote-vnet $RemotevNetId --allow-vnet-access --allow-forwarded-traffic --allow-gateway-transit
az network vnet peering create --name remote-aks --resource-group $REMOTE_RG --vnet-name myVNet --remote-vnet $AKSvNetId --allow-vnet-access --allow-forwarded-traffic --use-remote-gateways
az vm create --resource-group $REMOTE_RG --name myVM1 --image UbuntuLTS --generate-ssh-keys --public-ip-address myPublicIP-myVM1
