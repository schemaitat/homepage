pipeline{
    agent {
        label "jenkins-slave-hugo"
    } 
   
    stages {
        stage('Build static HTML') {
			steps{
                sh "rm -rf public"
                sh "hugo"
			}
		}   
        stage('Build docker image') {
            environment {
                DOCKER_REG = credentials('2f6d737b-5838-4339-a15e-060d120f1361')
            }
			steps{
				sh '''#!/bin/bash
                    docker login -u $DOCKER_REG_USR -p $DOCKER_REG_PSW registry.schemaitat.de
                    docker build -t web:1 .
                    docker tag web:1 registry.schemaitat.de/web:1
                    docker push registry.schemaitat.de/web:1 
                ''' 
			}
		}   
        stage("Redeploy"){
            steps{
                sh'''#!/bin/bash
                #kubectl config set-context --current --user jenkins --kubeconfig /home/jenkins/.kube/kubeconfig_jenkins.yaml
                kubectl rollout restart deployment nginx -n web --kubeconfig /home/jenkins/.kube/kubeconfig_jenkins.yaml 
                '''
            }
        }
    }        
}
