---
weight: 5
title: "Setting up a static homepage."
date: 2022-03-22T17:55:28+08:00
draft: false
author: "André"
description: "First blog post."
toc: true
tags: ["hello world"]
categories: ["general"]

---
>- Creating a nano node.
>- Installing Hugo.
>- Installing Jenkins.

## The host
### SSH

```bash
ssh-copy-id root@172.105.67.187 
```

### Firewall

We want to have two services be accessible from the public. 

```bash
    firewall-cmd --state
    firewall-cmd --get-default-zone
    firewall-cmd --zone=public --list-all
    firewall-cmd --zone=public --add-port=8080/tcp --permanent
    firewall-cmd --zone=public --add-port=80/tcp --permanent
    firewall-cmd --zone=public --add-port=443/tcp --permanent
    firewall-cmd --reload
    # check that the rule is active
    firewall-cmd --zone=public --list-all
```

## DNS

![homepage-dsn](homepage-dsn.png)


## Configuring the linode

`yum -y install wget tar git`

## Packages

### nginx

Check out the [nginx](https://docs.nginx.com/nginx/admin-guide/installing-nginx/installing-nginx-open-source/) website.

```bash
    yum install epel-release
    yum update
    yum install nginx
    # start service at reboot
    systemctl enable nginx
    # start service
    systemctl start nginx
    # check status
    systemctl status nginx
```

Since we want to usc jenkins to build the static html and copy it to a destination from which nginx serves our hompage we have to grant permissions. We use that standard folder and a `chmod -R jenkins:0 /usr/share/nginx/html`.

At this point we should already have working webpage which is accessible at http://your-domain, i.e. at port 80. In the next section we will add TLS encrpytion to make the website secure.

### SSL/TLS and nginx 

For more details have a look at this [tutorial](https://www.nginx.com/blog/using-free-ssltls-certificates-from-lets-encrypt-with-nginx/). 

First, we create a nginx config file which later will be automatically modified by certbot.

```bash
cat > /etc/nginx/conf.d/schemaitat.de.conf << EOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    root /usr/share/nginx/html;
    server_name schemaitat.de  www.schemaitat.de;
}
EOF
```

Next, we will install *certbot*. If you are running another OS [this](https://certbot.eff.org/instructions?ws=nginx&os=centosrhel8) website is very useful to determine the correct installation method for certbot. For CentOS-8 we have to do the following:

```bash
    # install snapd
    yum install snapd
    systemctl enable --now snapd.socket
    ln -s /var/lib/snapd/snap /snap
    reboot
    # install certbot
    snap install core
    snap refresh core
    snap install --classic certbot
    ln -s /snap/bin/certbot /usr/bin/certbot
    certbot --nginx
    nginx -t && nginx -s reload
```

The output should look something like this:

![nginx-confg](nginx-conf.png)

Now, we should be able to see our homepage, more precisely the nginx example page, being served at https://your-domain.

### hugo

Check out the [hugo](https://gohugo.io/) website.

```bash
    # download hugo prebuilt binary
    cd
    wget https://github.com/gohugoio/hugo/releases/download/v0.98.0/hugo_0.98.0_Linux-64bit.tar.gz 
    tar -xzf hugo_0.98.0_Linux-64bit.tar.gz
    chmod a+x hugo
    # move the binary to a location which is in $PATH
    mv hugo /usr/local/bin
    # cleanup
    rm hugo_0.98.0_Linux-64bit.tar.gz
    # Verify that hugo is executable
    which hugo
```

### Jenkins

Check out the [Jenkins](https://www.jenkins.io/doc/book/installing/linux/#red-hat-centos) install page for Cent-OS.

```bash
    sudo wget -O /etc/yum.repos.d/jenkins.repo \
        https://pkg.jenkins.io/redhat/jenkins.repo
    sudo rpm --import https://pkg.jenkins.io/redhat/jenkins.io.key
    sudo yum upgrade
    # Add required dependencies for the jenkins package
    sudo yum install java-11-openjdk
    sudo yum install jenkins
    # start jenkins service on start-up
    sudo systemctl enable jenkins
    sudo reboot
```

After reboot you can check the status of the service with `systemctl status jenkins`. The output shoud look like this: 

![jenkins-status](jenkins-status.png)

From the output you can extract the initial admin password, which you should change after first login. Furthermore, you can look at the process with `ps -afe | grep jenkins`, where you can also see that jenkins is running on port 8080.

## Set up Jenkins Pipeline

In our source repository we put a *Jenkinsfile*, wich defines the pipeline that should be executed. The idea ist to first build the static html with hugo and then copy the output to our root destination for nginx. This is an example for a very basic Jenkinsfile:
```jenkinsfile
pipeline{
    agent any

    stages {
        stage('Build static HTML') {
			steps{
                sh "rm -rf public"
                sh "hugo --cacheDir $HOME/hugo_cache"
			}
		}   
        stage("Update HTML"){
            steps{
                sh'''#!/bin/bash
                rm -rf /usr/share/nginx/html/*
                cp -r public/* /usr/share/nginx/html
                '''
            }
        }
    }        
}
```
