---
title: "Reproducible development setup"
date: 2023-01-07T20:39:35+01:00
draft: true
---


{{< admonition abstract >}}
**Things you get**
- A script which installs **oh-my-zsh** with customizable plugins and other useful tools like **tmux**.

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
