make kind-k8st-setup
kubectl delete configmap calico-config -n kube-system
kubectl delete ds calico-node -n kube-system
kubectl delete deploy calico-kube-controllers -n kube-system
kubectl create -f https://2023-01-24-v3-16-untagged.docs.eng.tigera.net/manifests/tigera-operator.yaml
kubectl patch deployment -n tigera-operator tigera-operator     -p '{"spec":{"template":{"spec":{"imagePullSecrets":[{"name": "tigera-pull-secret"}]}}}}'
kubectl create secret generic tigera-pull-secret     --type=kubernetes.io/dockerconfigjson -n tigera-operator     --from-file=.dockerconfigjson=/home/mazdak/secrets/docker_cfg.json
kubectl create -f https://2023-01-24-v3-16-untagged.docs.eng.tigera.net/manifests/custom-resources.yaml
===== [Enable/Configure EGW] =====
kubectl patch felixconfiguration.p default --type='merge' -p \
    '{"spec":{"egressIPSupport":"EnabledPerNamespaceOrPerPod"}}'
kubectl patch felixconfiguration.p default --type='merge' -p \
    '{"spec":{"policySyncPathPrefix":"/var/run/nodeagent"}}'
kubectl apply -f ippool.yaml
kubectl apply -f egw.yaml
kubectl get secret tigera-pull-secret --namespace=calico-system -o yaml | grep -v '^[[:space:]]*namespace:[[:space:]]*calico-system' | kubectl apply --namespace=calico-egress -f -
===== [ Create app] =====
kubectl annotate ns default egress.projectcalico.org/selector="egress-code == 'red'"
kubectl annotate ns default egress.projectcalico.org/namespaceSelector="projectcalico.org/name == 'calico-egress'"
