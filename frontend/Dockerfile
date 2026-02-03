FROM nginx:alpine

# Copy static files
COPY index.html /usr/share/nginx/html/

# Copy nginx config
COPY nginx-standalone.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
