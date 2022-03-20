FROM nginx:latest

COPY public /usr/share/nginx/html

RUN chown -R nginx:nginx /usr/share/nginx/html
RUN chmod -R a-rwx /usr/share/nginx/html
RUN chmod -R u+rx /usr/share/nginx/html
