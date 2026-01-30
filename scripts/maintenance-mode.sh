#!/bin/bash
# Maintenance Mode Control Script for Cerberus CTF Platform
# Usage: ./maintenance-mode.sh [on|off|status]

MAINTENANCE_FILE="/var/www/html/.maintenance"
NGINX_SERVICE="nginx"

show_help() {
    cat << EOF
Cerberus CTF Platform - Maintenance Mode Control

Usage: $0 [COMMAND]

Commands:
    on          Enable maintenance mode
    off         Disable maintenance mode
    status      Check maintenance mode status
    help        Show this help message

Examples:
    $0 on       # Enable maintenance mode
    $0 off      # Disable maintenance mode
    $0 status   # Check current status

Note: Requires sudo privileges to modify maintenance flag file.
EOF
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "Error: This script must be run with sudo"
        exit 1
    fi
}

enable_maintenance() {
    check_root
    
    echo "Enabling maintenance mode..."
    
    # Create maintenance flag file
    touch "$MAINTENANCE_FILE"
    
    # Reload nginx to apply changes
    if systemctl is-active --quiet $NGINX_SERVICE; then
        systemctl reload $NGINX_SERVICE
        if [ $? -eq 0 ]; then
            echo "✓ Maintenance mode ENABLED"
            echo "✓ Nginx reloaded successfully"
            echo ""
            echo "All traffic will now see the maintenance page."
            echo "To disable: $0 off"
        else
            echo "✗ Failed to reload Nginx"
            rm -f "$MAINTENANCE_FILE"
            exit 1
        fi
    else
        echo "✗ Nginx is not running"
        rm -f "$MAINTENANCE_FILE"
        exit 1
    fi
}

disable_maintenance() {
    check_root
    
    echo "Disabling maintenance mode..."
    
    # Remove maintenance flag file
    if [ -f "$MAINTENANCE_FILE" ]; then
        rm -f "$MAINTENANCE_FILE"
        
        # Reload nginx to apply changes
        systemctl reload $NGINX_SERVICE
        
        if [ $? -eq 0 ]; then
            echo "✓ Maintenance mode DISABLED"
            echo "✓ Nginx reloaded successfully"
            echo ""
            echo "The platform is now accessible to all users."
        else
            echo "✗ Failed to reload Nginx"
            exit 1
        fi
    else
        echo "Maintenance mode is already disabled"
    fi
}

check_status() {
    if [ -f "$MAINTENANCE_FILE" ]; then
        echo "Status: 🔴 MAINTENANCE MODE ENABLED"
        echo ""
        echo "The platform is currently showing the maintenance page to all visitors."
        echo "Maintenance file: $MAINTENANCE_FILE"
        echo "Created: $(stat -c %y "$MAINTENANCE_FILE" 2>/dev/null || stat -f %Sm "$MAINTENANCE_FILE" 2>/dev/null || echo 'Unknown')"
    else
        echo "Status: 🟢 NORMAL OPERATION"
        echo ""
        echo "The platform is accessible to all users."
    fi
    
    # Check nginx status
    if systemctl is-active --quiet $NGINX_SERVICE; then
        echo "Nginx: Running"
    else
        echo "Nginx: Not running ⚠️"
    fi
}

# Main
case "${1:-status}" in
    on|enable|start)
        enable_maintenance
        ;;
    off|disable|stop)
        disable_maintenance
        ;;
    status|check)
        check_status
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
