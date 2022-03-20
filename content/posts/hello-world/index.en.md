---
weight: 5
title: "Hello, World !"
date: 2021-11-14T17:55:28+08:00
lastmod: 2021-11-14T17:55:28+08:00
draft: true
author: "André"
description: "First blog post."

tags: ["hello world"]
categories: ["general"]

---
As part of my new webpage I decided to start a blog about things I find interesting, that I recently learned and my old and still active passion, mathematics.

I will start off by giving an end-to-end tutorial on how to  set up a webpage like this using a Kubernetes cluster. Surely there are more ad hoc ways to do this, but as part of my new job I learned to love k8s and its magic. Hence, this growing project is a hobby and at the same time an excercise for me.

 The main components of this setup are:
> - a domain
> - a git repo
> - a kubernetes cluster
> - a bunch of deployments and HELM charts
> - a Load Balancer
> - automation using Jenkins 
> - a static website generator, in my case *hugo*.

The goal is to have a running webpage, being automatically updated each time a push to the git repository happens.

Setting up this project assumes some basic knowledge about the Linux ecosystem, bash scripting, git, docker (images), kubernetes, HELM and networks.

<br>

Watch out for the next post :smiley: