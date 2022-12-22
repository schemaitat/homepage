pipeline{
    agent any

    environment{
        // look at local installation of hugo first if a 
        // installation with the wrong version exists
        PATH="${WORKSPACE}:${PATH}"
    }

    stages {
    	stage('Install hugo'){
		steps{
			sh'''#!/bin/bash
            set -x
            RELEASE=0.108.0
            # check if hugo is installed with the correct version
            LOCAL_HUGO_INSTALL=false

            which hugo
            if [ $? -ne 0 ]; then
                LOCAL_HUGO_INSTALL=true
            else
                hugo version | grep "${RELEASE}+extended"
                if [ $? -ne 0 ]; then
                    LOCAL_HUGO_INSTALL=true
                fi
            fi

            if [ "$LOCAL_HUGO_INSTALL" = "true" ]; then
                echo "Didn't find global hugo version with the required version $RELEASE."
                echo "Hence, using wget to install a local relase."
                wget https://github.com/gohugoio/hugo/releases/download/v${RELEASE}/hugo_extended_${RELEASE}_Linux-64bit.tar.gz
                tar -xzf hugo_${RELEASE}_Linux-64bit.tar.gz
                chmod +x ./hugo
                echo "Done."
            fi
			'''
		}
    	}
        stage('Build static HTML') {
		    steps{
			    sh'''#!/bin/bash
                set -x
                sed -i "s/{{COMMIT}}/${GIT_COMMIT:0:6}/g" config.toml
                sed -i "s/{{DATE}}/$(date '+%A %e %B %Y')/g" config.toml
                '''
                sh "rm -rf public"
			    sh "hugo --cacheDir $HOME/hugo_cache"
		    }
	    }   
        stage("Update HTML"){
    		steps{
                sh'''#!/bin/bash
                set -x
			    rm -rf /usr/share/nginx/html/*
                cp -r public/* /usr/share/nginx/html
                if [ -f $(pwd)/hugo ]; then
                    rm -rf ./hugo*
                fi
                '''
            }
        }
    }        
}
