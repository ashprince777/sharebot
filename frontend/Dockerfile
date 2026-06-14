# Serve pre-built static bundle via Nginx
FROM nginx:1.25-alpine

# Copy built files from host build directory to Nginx web root
COPY dist /usr/share/nginx/html

# Copy Nginx server configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Expose HTTP port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
