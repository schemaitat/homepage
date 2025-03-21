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
                uv sync 
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
                // add uv run to build with the 
                // correct python kernel (managed by uv)
                sh "uv run quarto render && hugo --cacheDir $HOME/hugo_cache"
            }
        }   

        stage("Update HTML"){
            steps{
                sh'''#!/bin/bash
                set -x
                rm -rf /usr/share/nginx/html/*
                cp -r public/* /usr/share/nginx/html
                '''
            }
        }

        stage("Add marimo wasm files to public"){
            steps{
                sh '''#!/bin/bash
                chmod +x ./scripts/install_marimo_notebooks.sh
                ./scripts/install_marimo_notebooks.sh /usr/share/nginx/html
                '''
            }
        }
    }        
}
