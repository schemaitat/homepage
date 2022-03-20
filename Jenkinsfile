pipeline{
    agent any

    stages {
        stage('Build static HTML') {
			steps{
                sh "env | grep -i jenkins"
                sh "rm -rf public"
                sh "hugo"
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
