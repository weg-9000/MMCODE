#!/bin/bash
# MMCODE Security Sandbox Network Rules
# =====================================
#
# Network isolation and access control for security tool sandbox
# - Restrict outbound connections to authorized ranges
# - Block dangerous network operations
# - Enable logging for security monitoring

set -euo pipefail

# Configuration
SANDBOX_INTERFACE="eth0"
ALLOWED_PRIVATE_RANGES=(
    "10.0.0.0/8"
    "172.16.0.0/12"
    "192.168.0.0/16"
    "127.0.0.0/8"
)
LOG_PREFIX="MMCODE-SANDBOX: "

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running with proper privileges
check_privileges() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root for iptables configuration"
        exit 1
    fi
}

# Backup existing rules
backup_rules() {
    log "Backing up existing iptables rules..."
    iptables-save > /tmp/iptables-backup-$(date +%Y%m%d-%H%M%S).rules || {
        warn "Failed to backup iptables rules"
    }
}

# Clear existing rules
clear_rules() {
    log "Clearing existing iptables rules..."
    
    # Set default policies to ACCEPT temporarily
    iptables -P INPUT ACCEPT
    iptables -P FORWARD ACCEPT
    iptables -P OUTPUT ACCEPT
    
    # Flush all rules
    iptables -F
    iptables -X
    iptables -t nat -F
    iptables -t nat -X
    iptables -t mangle -F
    iptables -t mangle -X
}

# Setup basic security rules
setup_basic_rules() {
    log "Setting up basic security rules..."
    
    # Allow loopback traffic
    iptables -A INPUT -i lo -j ACCEPT
    iptables -A OUTPUT -o lo -j ACCEPT
    
    # Allow established and related connections
    iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
    iptables -A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
    
    # Drop invalid packets
    iptables -A INPUT -m conntrack --ctstate INVALID -j LOG --log-prefix "${LOG_PREFIX}INVALID-IN: "
    iptables -A INPUT -m conntrack --ctstate INVALID -j DROP
    iptables -A OUTPUT -m conntrack --ctstate INVALID -j LOG --log-prefix "${LOG_PREFIX}INVALID-OUT: "
    iptables -A OUTPUT -m conntrack --ctstate INVALID -j DROP
}

# Setup sandbox-specific rules
setup_sandbox_rules() {
    log "Setting up sandbox-specific network rules..."
    
    # Allow DNS queries (needed for some tools)
    iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
    iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT
    
    # Allow NTP (time synchronization)
    iptables -A OUTPUT -p udp --dport 123 -j ACCEPT
    
    # Allow private network ranges for scanning
    for range in "${ALLOWED_PRIVATE_RANGES[@]}"; do
        log "Allowing access to private range: $range"
        
        # Allow TCP connections to private ranges
        iptables -A OUTPUT -d "$range" -p tcp -j ACCEPT
        iptables -A INPUT -s "$range" -p tcp -j ACCEPT
        
        # Allow UDP to private ranges
        iptables -A OUTPUT -d "$range" -p udp -j ACCEPT
        iptables -A INPUT -s "$range" -p udp -j ACCEPT
        
        # Allow ICMP to private ranges (for ping)
        iptables -A OUTPUT -d "$range" -p icmp -j ACCEPT
        iptables -A INPUT -s "$range" -p icmp -j ACCEPT
    done
    
    # Block common dangerous ports
    local dangerous_ports=(
        "135"    # RPC endpoint mapper
        "139"    # NetBIOS Session Service
        "445"    # SMB over IP
        "1433"   # SQL Server
        "3389"   # RDP
        "5985"   # WinRM HTTP
        "5986"   # WinRM HTTPS
    )
    
    for port in "${dangerous_ports[@]}"; do
        iptables -A OUTPUT -p tcp --dport "$port" -j LOG --log-prefix "${LOG_PREFIX}BLOCKED-DANGEROUS-PORT-$port: "
        iptables -A OUTPUT -p tcp --dport "$port" -j REJECT
    done
}

# Setup rate limiting
setup_rate_limiting() {
    log "Setting up rate limiting..."
    
    # Limit new connections per minute
    iptables -A OUTPUT -p tcp --syn -m limit --limit 100/min --limit-burst 200 -j ACCEPT
    iptables -A OUTPUT -p tcp --syn -j LOG --log-prefix "${LOG_PREFIX}RATE-LIMITED: "
    iptables -A OUTPUT -p tcp --syn -j DROP
    
    # Limit ICMP packets
    iptables -A OUTPUT -p icmp -m limit --limit 10/min -j ACCEPT
    iptables -A OUTPUT -p icmp -j LOG --log-prefix "${LOG_PREFIX}ICMP-LIMITED: "
    iptables -A OUTPUT -p icmp -j DROP
    
    # Limit UDP packets
    iptables -A OUTPUT -p udp -m limit --limit 50/min --limit-burst 100 -j ACCEPT
    iptables -A OUTPUT -p udp -j LOG --log-prefix "${LOG_PREFIX}UDP-LIMITED: "
    iptables -A OUTPUT -p udp -j DROP
}

# Block external internet access
setup_internet_blocking() {
    log "Setting up external internet blocking..."
    
    # Block access to known public DNS servers (except for essential services)
    local public_dns=(
        "8.8.8.8"
        "8.8.4.4"
        "1.1.1.1"
        "1.0.0.1"
        "208.67.222.222"
        "208.67.220.220"
    )
    
    for dns in "${public_dns[@]}"; do
        iptables -A OUTPUT -d "$dns" -p udp --dport 53 -j LOG --log-prefix "${LOG_PREFIX}BLOCKED-PUBLIC-DNS: "
        iptables -A OUTPUT -d "$dns" -p udp --dport 53 -j REJECT
        iptables -A OUTPUT -d "$dns" -p tcp --dport 53 -j LOG --log-prefix "${LOG_PREFIX}BLOCKED-PUBLIC-DNS: "
        iptables -A OUTPUT -d "$dns" -p tcp --dport 53 -j REJECT
    done
    
    # Block common internet services
    local internet_ports=(
        "80"     # HTTP
        "443"    # HTTPS
        "21"     # FTP
        "22"     # SSH (external)
        "23"     # Telnet
        "25"     # SMTP
        "110"    # POP3
        "143"    # IMAP
        "993"    # IMAPS
        "995"    # POP3S
    )
    
    for port in "${internet_ports[@]}"; do
        # Allow to private ranges, block to public
        for range in "${ALLOWED_PRIVATE_RANGES[@]}"; do
            iptables -A OUTPUT -d "$range" -p tcp --dport "$port" -j ACCEPT
        done
        
        # Block to everything else (public internet)
        iptables -A OUTPUT -p tcp --dport "$port" -j LOG --log-prefix "${LOG_PREFIX}BLOCKED-INTERNET-$port: "
        iptables -A OUTPUT -p tcp --dport "$port" -j REJECT
    done
}

# Setup security monitoring
setup_monitoring() {
    log "Setting up security monitoring rules..."
    
    # Log suspicious connection attempts
    iptables -A INPUT -p tcp --tcp-flags FIN,URG,PSH FIN,URG,PSH -j LOG --log-prefix "${LOG_PREFIX}NMAP-XMAS: "
    iptables -A INPUT -p tcp --tcp-flags ALL ALL -j LOG --log-prefix "${LOG_PREFIX}XMAS-SCAN: "
    iptables -A INPUT -p tcp --tcp-flags ALL NONE -j LOG --log-prefix "${LOG_PREFIX}NULL-SCAN: "
    iptables -A INPUT -p tcp --tcp-flags SYN,RST SYN,RST -j LOG --log-prefix "${LOG_PREFIX}SYN-RST: "
    iptables -A INPUT -p tcp --tcp-flags SYN,FIN SYN,FIN -j LOG --log-prefix "${LOG_PREFIX}SYN-FIN: "
    
    # Log port scanning attempts
    iptables -A INPUT -p tcp --dport 1:1023 -m recent --name portscan --set -j LOG --log-prefix "${LOG_PREFIX}PORTSCAN-DETECTED: "
    iptables -A INPUT -p tcp --dport 1:1023 -m recent --name portscan --update --seconds 60 --hitcount 10 -j DROP
}

# Set default policies
setup_default_policies() {
    log "Setting default policies..."
    
    # Default policies - be restrictive
    iptables -P INPUT DROP
    iptables -P FORWARD DROP
    iptables -P OUTPUT DROP
    
    # Log dropped packets (sample only to avoid log spam)
    iptables -A INPUT -m limit --limit 1/min -j LOG --log-prefix "${LOG_PREFIX}DROPPED-IN: "
    iptables -A OUTPUT -m limit --limit 1/min -j LOG --log-prefix "${LOG_PREFIX}DROPPED-OUT: "
}

# Verify rules
verify_rules() {
    log "Verifying iptables rules..."
    
    echo "=== INPUT Chain ==="
    iptables -L INPUT -n --line-numbers
    
    echo "=== OUTPUT Chain ==="
    iptables -L OUTPUT -n --line-numbers
    
    echo "=== FORWARD Chain ==="
    iptables -L FORWARD -n --line-numbers
    
    # Test basic connectivity
    log "Testing basic connectivity..."
    
    # Test loopback
    if ping -c 1 127.0.0.1 >/dev/null 2>&1; then
        log "✓ Loopback connectivity working"
    else
        error "✗ Loopback connectivity failed"
    fi
    
    # Test private network (if available)
    if ping -c 1 -W 2 192.168.1.1 >/dev/null 2>&1; then
        log "✓ Private network connectivity working"
    else
        warn "⚠ Private network connectivity not available (may be expected)"
    fi
    
    # Test external internet blocking
    if ping -c 1 -W 2 8.8.8.8 >/dev/null 2>&1; then
        warn "⚠ External internet access detected (review rules)"
    else
        log "✓ External internet access blocked"
    fi
}

# Save rules
save_rules() {
    log "Saving iptables rules..."
    
    # Save rules to standard location
    if command -v iptables-save >/dev/null 2>&1; then
        iptables-save > /etc/iptables/rules.v4 2>/dev/null || \
        iptables-save > /etc/iptables.rules 2>/dev/null || \
        warn "Could not save rules to standard location"
        
        log "Rules saved successfully"
    else
        warn "iptables-save not available"
    fi
}

# Main execution
main() {
    log "MMCODE Security Sandbox Network Configuration"
    log "============================================="
    
    check_privileges
    backup_rules
    clear_rules
    setup_basic_rules
    setup_sandbox_rules
    setup_rate_limiting
    setup_internet_blocking
    setup_monitoring
    setup_default_policies
    verify_rules
    save_rules
    
    log "Network security rules configured successfully"
    log "Monitor logs with: tail -f /var/log/kern.log | grep 'MMCODE-SANDBOX'"
}

# Handle script termination
cleanup() {
    warn "Script interrupted, rules may be incomplete"
    exit 130
}

trap cleanup SIGINT SIGTERM

# Run main function
main "$@"