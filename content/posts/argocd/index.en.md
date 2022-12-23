---
weight: 5
title: "Argo CD"
date: 2022-12-22T17:55:28+08:00
draft: true
math: false
author: "André"
description: "Tutorial on Argo CD."
toc: false
tags: ["tutorial", "argo", "cd", "kubernetes"]
categories: ["tutorial", "kubernetes"]
---

# Introduction

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
    C -->|One| D[Result one]
    C -->|Two| E[Result two]