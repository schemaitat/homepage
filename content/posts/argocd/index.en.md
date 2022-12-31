---
weight: 5
title: "Kubernetes as a service & Argo CD"
date: 2022-12-31T09:55:28+08:00
draft: false
math: false
author: "André"
description: "Tutorial on Argo CD."
toc: true
tags: ["tutorial", "linode", "provisioning", "argo", "cd", "kubernetes"]
categories: ["tutorial", "kubernetes", "dev-ops"]
---

{{< admonition abstract >}}
**Things you get**
- A running kubernetes cluster with any deplyoment (yaml, helm, kustomize) you want in less than 5 minutes.
- Easy tear down of the cluster (when you don't need it) to save costs.
- Reproducibility and idempotency of the create and delete steps.

**Things you learn**
1. Setting up a kubernetes cluster with the **Linode Kubernetes Engine** (LKE).
2. Deploying software with **Argo CD** and the **app of apps** schema.

**Prerequisits**
- For 1. a Linode Account.
- Basic bash and kubernetes knowledge, see also <a href="{{< ref "k8s-basics" >}}">kubernetes basics</a>.
- jq, yq, curl, helm, kubectl, linode-cli or a docker container containing all this stuff.

**git repo**
- [schemaitat/k8s-cluster](https://github.com/schemaitat/k8s-cluster)

{{< /admonition >}}

## Introduction

Initially, I wanted to learn something about *apache airflow*. 
After setting up a local kubernetes cluster with minikube, installing everything bare hands,
I quickly realized that my local setup didn't have enough power to really get going.
Another issue with the manual workflow is that I had to make changes to the cluster and the deployments quite frequently.

Eventually, I decided to automate the wohle process of creating a kubernetes cluster and deploying an initial software stack.

In this post we will have a look how to create a kubernetes cluster with the LKE (Linode Kubernetes Engine) and how to deploy
our software with Argo CD.

More details on airflow and how to leverage the power of kubernetes + airflow will follow in another post.

Other use cases to be explored would be handling heavy workloads with a highly 
performant, but short living, cluster.
This could be batch workload or training a ML model with a GPU cluster.

Hopefully, I will be able to write another post about heavy batch workload with julia and my work in [schemaitat/sparse_dot_topn_julia](https://github.com/schemaitat/sparse_dot_topn_julia). 

## The kubernetes cluster

The main work for setting up the cluster and installing Argo CD is done in [start.sh](https://github.com/schemaitat/k8s-cluster/blob/main/start.sh).
The script is divided into eight steps (I) - (VIII). Setting up the cluster is done in steps (I) - (IV).

The first (and only) argument for the script is the path to a configuration yaml, which defines the cluster we want to create. An example would be:

```yaml
cluster: k8s-dev
kubernetes-version: 1.24
region: eu-central
tags:
- dev
- test
nodePools:
- type: g6-standard-2
  count: 1
- type: g6-standard-4
  count: 1
```

You can get a list of all types with costs by using `linode-cli linodes types`. The value of `cluster` is a unique name for the cluster. 
The cluster configuration will be parsed during step (I), the create-cluster step:

{{< gist schemaitat 89796184fe4ac2892f31c994514425a8 >}}

In step (II) we wait for the cluster to be ready. This is checked by waiting for all nodes in the cluster to be ready.

{{< gist schemaitat bd27b6823cb9917637d1695553e4d12b >}}

Note, that `grep` has a non-zero return code if no matches are found. That is why we enclose the while loop in `set +e` and `set -e` marks.

In step (III), after the cluster is ready, we copy the *kubeconfig* to our local machine. Note that the default location for the kubeconfig is defined in `$KUBECONFIG`.

```bash
export KUBECONFIG=~/${CLUSTER}-kubeconfig.yaml
log_notice "(III) Copying kubeconfig to $KUBECONFIG."
linode-cli lke kubeconfig-view $CLUSTER_ID --json --no-headers | jq '.[].kubeconfig' | sed 's|"||g' | base64 -D > $KUBECONFIG
chmod 700 $KUBECONFIG
```

In step (IV) we wait for the kubernetes api to be ready.
This is necessary for the following steps and setting up Argo CD.

{{< gist schemaitat cb40f1f5dfdea0b9e2e3e719c48466ea >}}

After having run steps (I) - (IV) you should have a running kubernetes cluster
and a local copy of the kubeconfig accessible by `kubectl`.

## Argo CD

Next, we will look at Argo CD. This is a deployment tool aiming to synchronize a certain state of an application. To this end we have a subfolder `charts/argo-cd` in our repository, which contains a so-called umbrella Helm Chart. This Helm Chart references to the original Argo CD Helm Chart, but also contains a customizable `values.yaml`. 

Furthermore, we have a subfolder `apps` in our repository, containing a Helm Chart, which defines the `root` application.
The `root` application contains templates, which are themselves applications.
Since Argo CD tries to synchronize the `root` applicaiton, it will also synchronize every change made in any of the templates, e.g. the child applications.

The steps to install Argo CD and all applications in `apps` are:

1. Install Argo CD with helm using helm install.
2. By having an Argo CD application in the apps folder, Argo CD will eventually maintain itself. 
3. Install the root application  (with `kubectl apply -f`).

The idea of having a `root` application which synchronizes applications is called the **app of apps** schema. 
The dependencies look similar to

{{< mermaid >}}
graph LR;
    A[root <br> application] -->|sync| B(./apps)
    B --> C(Chart.yaml)
    B --> D(values.yaml)
    B --> E[apps/templates]
    E --> F(argocd.yaml)
    E --> G(prometheus.yaml)
    E --> H(airflow.yaml)
{{< /mermaid >}}

In this case Argo CD itself, Prometheus and Airflow are maintained by Argo CD and are installed after the `root` application is applied.

In our `start.sh` script, the just described steps are steps (V) - (VIII):
```bash
log_notice "(V) Creating namespaces"
namespaces="argocd monitoring airflow"
for ns in $namespaces; do
    kubectl create ns $ns
done

log_notice "(VI) Installing Argo CD"
# install argocd  and set up namespaces
helm dep update charts/argo-cd
helm install argo-cd charts/argo-cd/ -n argocd


log_notice "(VII) Waiting for all Argo CD deployments to be available"
#wait for argo cd to be deployed
argo_deployments=$(kubectl get deployments -n argocd --no-headers=true | awk '{print $1}')
for dep in $argo_deployments; do
    log_info "Waiting for deployment $dep to be available ..."
    kubectl wait deployment -n argocd $dep --for condition=Available=True --timeout=300s
done

log_notice "(VIII) Installing root application (app of apps)"
# install root application
kubectl apply -f apps/templates/root.yaml
```

In step (VII) we wait for Argo CD to be fully functioning.
This ensures that Argo CD sees the `root` application just after it is truely able to install apps.

## Tear down and cleanup

After having created a cluster with deployments, we eventually want to tear it down. This is quite easy with the linode cli, but we have to look out for possible artifacts, which are automatically created by Argo CD, most notably `volumes`. 

The following script deletes the cluster and remembers volumes which had been attached to one of the nodes. 
After the cluster is deleted, the function `delete_volume` deletes the volume with given id. 
Unfortunately, to my current knowledge, there isn't a neat way to check if a volume is still attached to a node.
Thats why we "try" to delete the volume until it is detached.

{{< gist schemaitat 6af33ebbaec0c248d56caf75b61089c4 >}}

In case this didn't work for some reason, the script [cleanup_volumes.sh](https://github.com/schemaitat/k8s-cluster/blob/main/cleanup_volumes.sh) tries to delete all volumes which have a `null` value for the `node_id`. 
