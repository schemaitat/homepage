pipeline{
    agent any

    stages {
        stage('Install submodules'){
            steps{
                sh "git submodule update --init --recursive"
            }
        }
    	stage('Install hugo'){
		steps{
			sh'''#!/bin/bash
            RELEASE=0.108.0
			wget https://github.com/gohugoio/hugo/releases/download/v${RELEASE}/hugo_${RELEASE}_Linux-64bit.tar.gz
			tar -xzf hugo_${RELEASE}_Linux-64bit.tar.gz
			chmod +x ./hugo
			'''
		}
    	}
        stage('Build static HTML') {
		steps{
			sh'''#!/bin/bash
            sed -i "s/{{COMMIT}}/${GIT_COMMIT:0:6}/g" config.toml
            sed -i "s/{{DATE}}/$(date '+%A %e %B %Y')/g" config.toml
            '''
            sh "rm -rf public"
			sh "./hugo --cacheDir $HOME/hugo_cache"
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
