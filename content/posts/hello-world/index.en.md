---
weight: 5
title: "Hello, World !"
date: 2022-03-22T17:55:28+08:00
draft: false
author: "André"
description: "First blog post."
toc: false
tags: ["hello world"]
categories: ["general"]

---
As part of my new webpage I decided to start a blog about things I find interesting, that I recently learned and my old and still active passion, mathematics.

I will start off by giving an end-to-end tutorial on how to  set up a webpage like this. 

In the fury of trying to decentralize everything, I first did this whole setup in a small (three node) kubernetes cluster. 

This method has surely its advantages:
>- everyhing is yaml, hence easy to reproduce,
>- during deployment no downtime due to k8s,
>- load balancing is easy,
>- fun to see all components interactig.

 However, after a short time, I realized that it is much cheaper and probably as quick to set up a webpage like this in a single tiny linux box. Acutally this one runs on a Cent OS VM with 1 CPU and 1 GB memory.

In the next post, I will show you how to do this with a static website generator. The main ingredients are 

>- a tiny bit of linux hacking,
>- nginx as webserver,
>- cert-manager for TLS encryption,
>- hugo as static website generator,
>- jenkins as automation tool.

See you for the next post :grin: