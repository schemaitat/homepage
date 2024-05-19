pipeline{
    agent any

    environment{
        // look at local installation of hugo first if a 
        // installation with the wrong version exists
        PATH="${HOME}/bin:${WORKSPACE}:${PATH}"
    }

    stages {
        stage('Update submodules') {
            steps{
                sh "git submodule update --init --recursive"
            }
        }   

        stage('Install binaries'){
            steps{
                sh'''#!/bin/bash
                chmod +x ./scripts/install.sh
                ./scripts/install.sh
                '''
            }
        }

        stage('Create python venv and install packages'){
            steps{
                sh'''#!/bin/bash
                # as required by pyproject
                uv venv --python 3.11
                source .venv/bin/activate
                poetry install
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
                sh "poetry run quarto render && hugo --cacheDir $HOME/hugo_cache"
            }
        }   

        stage("Update HTML"){
            steps{
                sh'''#!/bin/bash
                set -x
                rm -rf /usr/share/nginx/html/*
                cp -r public/* /usr/share/nginx/html
                if [ -f ${WORKSPACE}/hugo ]; then
                    rm -rf ./hugo*
                fi
                '''
            }
        }
    }        
}
