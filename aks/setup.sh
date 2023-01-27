====== Installing AKS ====== (documented)
az group create --name mazdak-rg --location eastus
az aks create --resource-group mazdak-rg --name calico-cluster --location eastus --pod-cidr 192.168.0.0/16 --network-plugin none
az aks get-credentials --resource-group mazdak-rg --name calico-cluster
kubectl create -f https://docs.tigera.io/manifests/tigera-operator.yaml
kubectl create secret generic tigera-pull-secret --type=kubernetes.io/dockerconfigjson -n tigera-operator --from-file=.dockerconfigjson=/home/mazdak/.banzai/secrets/docker_cfg.json
kubectl create -f custom-resources-calico-cni.yaml
watch kubectl get tigerastatus
kubectl create -f /home/mazdak/.banzai/secrets/license.yaml
watch kubectl get tigerastatus
===== Deploying EGW ===== (documented)
kubectl patch felixconfiguration.p default --type='merge' -p '{"spec":{"egressIPSupport":"EnabledPerNamespace"}}'
kubectl patch felixconfiguration.p default --type='merge' -p '{"spec":{"policySyncPathPrefix":"/var/run/nodeagent"}}'
kubectl apply -f ippool.yaml
kubectl get secret tigera-pull-secret --namespace=calico-system -o yaml | grep -v '^[[:space:]]*namespace:[[:space:]]*calico-system' | kubectl apply --namespace=default -f -
kubectl apply -f egw.yaml
===== Deploying an app ===== (documented)
kubectl annotate ns data-analysis egress.projectcalico.org/selector="egress-code == 'red'"
kubectl annotate ns data-analysis egress.projectcalico.org/namespaceSelector="projectcalico.org/name == 'default'"
k apply -f app.yaml
===== Setup Calico BGP =====
k patch installation default -p '{"spec": {"calicoNetwork": {"bgp": "Enabled"}}}'
calicoctl --allow-version-mismatch patch node aks-nodepool1-32680072-vmss000000 -p '{"spec": {"bgp": {"routereflectorclusterid": "244.0.0.1"}}}'
kubectl label node aks-nodepool1-32680072-vmss000000 route-reflector=true
kubectl apply -f bgp-rr.yaml
===== Azure BGP Setup ===== (documented)
az network vnet subnet create -n RouteServerSubnet -g MC_mazdak-rg_calico-cluster_eastus --vnet-name aks-vnet-39948919 --address-prefix 10.225.0.0/24
az network public-ip create --name RouteServerIP -g mazdak-rg --version IPv4 --sku Standard
az network routeserver create -n myRouteServer -g mazdak-rg --hosted-subnet /subscriptions/058e3078-8970-434e-a2f0-98a72d053ea9/resourceGroups/MC_mazdak-rg_mazdak-cluster_eastus/providers/Microsoft.Network/virtualNetworks/aks-vnet-39948919/subnets/RouteServerSubnet --public-ip-address RouteServerIP
az network routeserver peering create --name RR1 --peer-ip 10.224.0.4 --peer-asn 64512 --routeserver myRouteServer -g mazdak-rg
===== Azure Test setup ===== (documented)
az network vnet create --name myVNet --resource-group mazdak-bz-1tyr --address-prefixes 10.0.0.0/16 --subnet-name Subnet1 --subnet-prefix 10.0.0.0/24
# Get the id for myVirtualNetwork1.
vNet1Id=$(az network vnet show --resource-group mazdak-bz-1tyr --name myVNet --query id --out tsv)
# Get the id for myVirtualNetwork2.
vNet2Id=$(az network vnet show --resource-group MC_mazdak-bz-1tyr_mazdak-bz-1tyr_eastus2 --name aks-vnet-33410049 --query id --out tsv)
az network vnet peering create --name peering1-2 --resource-group mazdak-bz-1tyr --vnet-name myVNet --remote-vnet $vNet2Id --allow-vnet-access --allow-forwarded-traffic --use-remote-gateways
az network vnet peering create --name peering2-1 --resource-group MC_mazdak-bz-1tyr_mazdak-bz-1tyr_eastus2 --vnet-name aks-vnet-33410049 --remote-vnet $vNet1Id --allow-vnet-access --allow-forwarded-traffic --allow-gateway-transit
az vm create --resource-group mazdak-bz-1tyr --name myVM1 --image UbuntuLTS --generate-ssh-keys --public-ip-address myPublicIP-myVM1
