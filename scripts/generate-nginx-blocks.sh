# Wildcard DNS Nginx Block Generator
# For CTF Challenge instances from Docker Orchestrator
# Generates server blocks for *.challenges.ctf.com

#!/bin/bash

# Configuration
NGINX_SITES_AVAILABLE="/etc/nginx/sites-available"
NGINX_SITES_ENABLED="/etc/nginx/sites-enabled"
TEMPLATE_FILE="/etc/nginx/templates/challenge.conf.template"
LOG_DIR="/var/log/nginx/challenges"
CERTBOT_ENV="/etc/letsencrypt/env"

# Challenge container detection
ORCHESTRATOR_SOCKET="/var/run/docker.sock"
ORCHESTRATOR_LABEL="ctf.challenge"

ensure_directories() {
    mkdir -p "$NGINX_SITES_AVAILABLE"
    mkdir -p "$NGINX_SITES_ENABLED"
    mkdir -p "$LOG_DIR"
    mkdir -p "$(dirname "$TEMPLATE_FILE")"
}

create_template() {
    cat > "$TEMPLATE_FILE" << 'EOF'
# Challenge Instance: {challenge_name}
# Generated: {timestamp}
# Container: {container_id}

server {
    listen 80;
    server_name {hostname};

    # Challenge instance proxy
    location / {
        proxy_pass http://{container_ip}:{container_port}/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long-running challenges
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # WebSocket support
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }

    # Logging
    access_log /var/log/nginx/challenges/{hostname}_access.log;
    error_log /var/log/nginx/challenges/{hostname}_error.log;
}
EOF
}

generate_for_container() {
    local container_id="$1"
    local container_ip="$2"
    local container_port="$3"
    local challenge_name="$4"
    local hostname="${challenge_name}.challenges.ctf.com"
    
    local conf_file="${NGINX_SITES_AVAILABLE}/${hostname}.conf"
    local timestamp=$(date -Iseconds)
    
    # Generate configuration from template
    sed -e "s/{hostname}/${hostname}/g" \
        -e "s/{container_ip}/${container_ip}/g" \
        -e "s/{container_port}/${container_port}/g" \
        -e "s/{challenge_name}/${challenge_name}/g" \
        -e "s/{timestamp}/${timestamp}/g" \
        -e "s/{container_id}/${container_id:0:12}/g" \
        "$TEMPLATE_FILE" > "$conf_file"
    
    # Enable the site
    ln -sf "$conf_file" "${NGINX_SITES_ENABLED}/${hostname}.conf"
    
    echo "Generated: $hostname -> $container_ip:$container_port"
}

remove_for_hostname() {
    local hostname="$1"
    local conf_file="${NGINX_SITES_AVAILABLE}/${hostname}.conf"
    
    rm -f "$conf_file"
    rm -f "${NGINX_SITES_ENABLED}/${hostname}.conf"
    
    echo "Removed: $hostname"
}

reload_nginx() {
    nginx -t && systemctl reload nginx
    echo "Nginx reloaded"
}

# Main entry point for Docker events
handle_container_event() {
    local action="$1"
    local container_id="$2"
    
    case "$action" in
        start|create)
            # Get container info from orchestrator
            local container_info=$(get_container_info "$container_id")
            if [ -n "$container_info" ]; then
                generate_for_container $container_info
                reload_nginx
            fi
            ;;
        stop|die)
            local hostname=$(get_hostname_from_container "$container_id")
            if [ -n "$hostname" ]; then
                remove_for_hostname "$hostname"
                reload_nginx
            fi
            ;;
    esac
}

# Get container information from orchestrator
get_container_info() {
    local container_id="$1"
    # This would integrate with your Docker Orchestrator service
    # Example: curl -s "${ORCHESTRATOR_API}/containers/${container_id}"
    # Expected format: ip:port:challenge_name
    echo ""
}

get_hostname_from_container() {
    local container_id="$1"
    # Look up hostname from stored mapping
    echo ""
}

# Watch Docker events (run as daemon)
watch_docker_events() {
    docker events --filter "label=${ORCHESTRATOR_LABEL}" \
        --format "{{.Action}} {{.Actor.ID}}" | \
    while read action container_id; do
        handle_container_event "$action" "$container_id"
    done
}

# Initial sync - generate configs for all running challenge containers
sync_all_containers() {
    echo "Syncing all challenge containers..."
    # docker ps --filter "label=${ORCHESTRATOR_LABEL}" -q | \
    # while read container_id; do
    #     get_container_info "$container_id" | \
    #     while read info; do
    #         generate_for_container $info
    #     done
    # done
    # reload_nginx
    echo "Sync complete"
}

# Initialize
ensure_directories
create_template

# Usage info
case "${1:-help}" in
    generate)
        shift
        generate_for_container "$@"
        reload_nginx
        ;;
    remove)
        shift
        remove_for_hostname "$1"
        reload_nginx
        ;;
    watch)
        watch_docker_events
        ;;
    sync)
        sync_all_containers
        ;;
    init)
        create_template
        echo "Template created at $TEMPLATE_FILE"
        ;;
    *)
        echo "Usage: $0 {generate|remove|watch|sync|init}"
        echo ""
        echo "Commands:"
        echo "  generate <id> <ip> <port> <name>  - Generate config for a container"
        echo "  remove <hostname>                - Remove config for a hostname"
        echo "  watch                            - Watch Docker events for auto-generation"
        echo "  sync                             - Sync all running containers"
        echo "  init                             - Create template file"
        exit 1
        ;;
esac
