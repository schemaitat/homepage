---
weight: 5
title: "kubernetes basics"
date: 2021-11-21T13:04:28+08:00
lastmod: 2021-11-21T13:04:28+08:00
draft: false
author: "André"
description: "An introduction to kubernetes."

tags: ["k8s", "kubernetes", "cluster", "deployment", "nginx", "linode" ]
categories: ["cloud", "kubernetes"]
---
# Introduction

In this post, we will set up a Kubernetes cluster with [Linode](https://www.linode.com/) and deploy a dummpy webpage.
Linode is still the most transparent and user-friendly vendor I know of.

If you want to learn more about Kubernetes, I can recommend the [kubernetes 101](https://kube101.jeffgeerling.com/) tutorial by Jeff Geerling.


In another post, we will have a look at more advanced deplyoments like the one shown below, consisting of a basic setup to build and deploy a webpage. The main components would be 

- ingress (used together with an external load balancer)
- docker registry (image registry)
- jenkins (build pipeline)
- cert manager (TLS encryption)
- nginx server (webpage)

{{< image src="k8s-overview.png" caption="Create the cluster (2)" >}}

# kubectl

For this post, I show all steps for macOS executed in *zsh*. For other operating systems have a look at [https://kubernetes.io/docs/tasks/tools/](https://kubernetes.io/docs/tasks/tools/). 

First, check if kubectl is already installed.

```bash
if command kubectl &> /dev/null; then
    echo "kubectl already installed."
    echo "See: $(which kubectl)."
    exit
fi
```

If that is the case you are ready to go. Otherwise, let us download the latest binary.

```bash
cd
# rel can by any other valid release
rel=$(curl -L -s https://dl.k8s.io/release/stable.txt)
curl -LO "https://dl.k8s.io/release/${rel}/bin/darwin/amd64/kubectl"
# make the binary executable
chmod +x ./kubectl
# move to standard directory
sudo mv ./kubectl /usr/local/bin/kubectl
```

You can also move the binary to any other place as long as the absolute path of the base directory appears in the environment variable `$PATH`. As always, to persist changes like `export PATH=$PATH:/path/to/kubectl`, make sure to add that to your `.zshrc`.

You can verify the installation by typing `kubectl version`. 

To ease your life, we use an alias for kubectl and enable autocompletion. If you use a *zsh* terminal, don't forget to append autocompletion to your `.zshrc` file.

```bash
alias k="kubectl"
complete -F __start_kubectl k
source <(kubectl completion zsh)
```

The change takes effect after your .zshrc has been sourced. 


## the cluster

As already mentioned, I prefer Linode as Cloud Provider. However, you are free to choose another one, since the goal is to have a running Kubernetes cluster.

If you don't already have a Linode account, go to [Linode](https://www.linode.com/) and register. Once you are logged in, choose "Kubernetes" on the left panel and click "Create Cluster".

<br>
{{< image src="k8s-1.png" src_s="k8s-1.png" src_l="k8s-1.png" caption="Create the cluster (1)">}} 
<br>

Next, you choose a label for your cluster, a region where the nodes will live and which type of nodes you want to use. For the region, it makes sense to pick a geographically close one. This reduces the latency.

For the tutorial, I chose two Linodes with Shared CPU and 2 GB memory. However, to have enough redundancy, and to make Kubernetes what it is supposed to do, you should have three or more nodes.

<br>
{{< image src="k8s-2.png" caption="Create the cluster (2)" >}}
<br>

{{< admonition info >}}
Linode's billing is fully transparent. Each active resource like a node, a Load Balancer or a PVC costs a fixed amount per month, independent of its utilization. That makes your bill entirely predictable.
{{< /admonition >}}

While the nodes are starting up, you can already download the cluster specific `kubeconfig.yaml`.

<br>
{{< image style="padding: 5em" src="k8s-3.png" caption="Create the cluster (3)" >}}
<br>

To make the kubeconfig available to kubectl, the `$KUBECONFIG` variable is used. I like to have my kubeconfig at `~/kubeconfig.yaml` and have accordingly added `export KUBECONFIG=~/kubeconfig.yaml` to my `.zshrc`. 

{{< admonition info >}}
Also, make sure to set permissions. Anyone with the kubeconfig file has full access to the cluster.
{{< /admonition >}}

Set the permissions to 0400 (which I usually cannot remember). Instead, I always use the following, which is much easier to remember.

```bash
chmod a-rwx $KUBECONFIG
chmod u+r $KUBECONFIG
```

If everything went as expected, you can verify the setup by typing `k get nodes`. The output should show all nodes in your cluster. 

## a toy web app

Our first deployment will be a toy web application running on an Nginx webserver. Later, we will refine this deployment to host our *productive* website.

> With docker we would simply do a
>```bash
>docker run --rm -d -p 8080:80 nginx:latest
>```
>That would start a single Nginx container with its port 80 being forwarded to port 8080.
>You can check that the service is running with a `curl localhost:8080`.

In Kubernetes, we have to define a deployment. The `deployment.yaml` looks as follows:

```yaml 
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
  namespace: web
  labels:
    app: nginx
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:latest
        ports:
        - containerPort: 80
```

Before applying the yaml, we create a namespace **web**, which bundles all deployments regarding our web application. Then, we can apply the deployment and watch for pods to start.

```bash
k create ns web
k apply -f deployment.yaml
k get pods -n web -w
```

Now, we have a single pod with an Nginx server running in it. To make the web app accessible, we first have to deploy a *service*:

```yaml
apiVersion: v1
kind: Service
metadata:
  namespace: web
  name: nginx-service
spec:
  selector:
    app: nginx
  type: ClusterIP
  ports:
  - protocol: TCP
    port: 80
    targetPort: 80
```

{{< admonition info >}}
The `targetPort` must match the port the Nginx server is listening on. The `spec.selector` is responsible for assigning pods to the service, as defined in `spec.selector.matchLabels` in the deployment.
{{< /admonition >}}

By using kubectl we can forward the service port to our local network:

```bash
k port-forward -n web svc/nginx-service 8001:80
```

You should now be able to see a welcome page at `localhost:8001`. 

Another way to expose the service is to change `spec.type` to `NodePort`. That opens a static port on the node IP address. The port range is 30000-32767. Let us deploy the following service:

```yaml
apiVersion: v1
kind: Service
metadata:
  namespace: web
  name: nginx-service-node-port
spec:
  selector:
    app: nginx
  type: NodePort
  ports:
  - protocol: TCP
    port: 80
    targetPort: 80
    nodePort: 31100
```

Next, we have to find the external IP of one of the nodes. You can inspect `k get nodes -o wide` or get one IP directly by using the json output format together with *jq*:

```bash
IP=$(k get nodes -o json | jq '.items[0].status.addresses | .[] | select(.type == "ExternalIP") | .address' | sed 's/\"//g')
```

You can then check if the service works by curling `$IP:31100`.


I hope you got a first impression of how Kubernetes works and how to apply deployments.

See you for the next post :smiley: