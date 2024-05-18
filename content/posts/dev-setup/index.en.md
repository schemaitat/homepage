---
title: "Reproducible development setup"
date: 2024-05-17T13:04:28+02:00
draft: false
author: "André"
description: "First blog post."
toc: false
tags: ["tutorial linux"]
categories: ["tutorial"]
---
{{< admonition abstract >}}
**Things you get**
- A script that installs **oh-my-zsh** with customizable plugins and other useful tools like **tmux** and custom scripts.

**Prerequisites**
- Basic Linux and bash knowledge.

**Git repository**
- [schemaitat/vscode-dev-container](https://github.com/schemaitat/vscode-dev-container)
{{< /admonition >}}

## Introduction
Originally, I wanted to have a reproducible vscode devcontainer, i.e. a docker container that 
looks similar to my local development setup. This task reduces to defining an [installation script
](https://github.com/schemaitat/vscode-dev-container/blob/main/zsh-in-docker.sh) that installs things like oh-my-zsh (with plugins), packages like vim and tmux and aliases.

## How to

The script is based on [zsh-in-docker](https://github.com/deluan/zsh-in-docker) and contains some more configuration paramters. The script works like a cli and uses the bash `getopts` functionality to parse the arguments.

A dockerfile for you vscode devcontainer could the look similar to:

```Dockerfile
# This is only used for developing the zsh-in-docker script, but can be used as an example.

FROM debian:latest

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    # install a user that can run sudo without password
    && useradd -s /bin/bash --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && apt-get update \
    && apt-get install -y sudo wget curl \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    # cleanup
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

USER $USERNAME

RUN sh -c "$(wget -qO - https://raw.githubusercontent.com/schemaitat/vscode-dev-container/main/zsh-in-docker.sh)" -- \\
    -d https://raw.githubusercontent.com/schemaitat/dotfiles/master/.vimrc \
    -d https://raw.githubusercontent.com/schemaitat/dotfiles/master/.tmux.conf \
    -i vim -i tmux -i htop \
    -p git -p git-auto-fetch \
    -p https://github.com/zsh-users/zsh-autosuggestions \
    -p https://github.com/zsh-users/zsh-completions \
    -p https://github.com/zsh-users/zsh-syntax-highlighting \
    -a 'CASE_SENSITIVE="true"' \
    -a 'HYPHEN_INSENSITIVE="true"' \
    -a 'export TERM=xterm-256color' \
    -s /tmp/post.sh

ENTRYPOINT [ "/bin/zsh" ]
```

If you put this into a file called `.devcontainer/Dockerfile` you are instantly ready to run your project in a fully configured dev environment.

Of course, the base image debian:latest may be changed to some base image suitable to your project, e.g. a python or whatever base image.

Feel free to modify the script to your needs :thumbsup: