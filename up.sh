echo "INFO: Building website."
hugo
echo "INFO: Clearing html folder on webserver."
ssh root@139.162.179.56 'rm -rf /usr/share/nginx/html/*'
echo "INFO: Copying local sources to webserver."
scp -r public/* root@139.162.179.56:/usr/share/nginx/html
