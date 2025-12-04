# MMCODE Security Sandbox
## Docker-Based Isolated Security Tool Environment

### Overview

The MMCODE Security Sandbox provides a secure, isolated environment for executing security testing tools with comprehensive monitoring and access controls.

### Features

- **Security Isolation**: Non-root execution with network and resource restrictions
- **Tool Integration**: Pre-installed Nmap, Nuclei, Masscan, and OWASP ZAP
- **Resource Monitoring**: CPU, memory, and I/O usage tracking
- **Network Controls**: Private network access only, external internet blocking
- **Audit Logging**: Comprehensive logging of all tool executions
- **Health Monitoring**: Continuous health checks and service monitoring

### Quick Start

1. **Build the container:**
   ```bash
   cd docker/security-sandbox
   docker-compose build
   ```

2. **Start the sandbox:**
   ```bash
   docker-compose up -d
   ```

3. **Check health:**
   ```bash
   docker-compose exec mmcode-sandbox python3 /opt/security-tools/healthcheck.py
   ```

### Container Structure

```
/home/mmcode-runner/          # User home directory
├── nuclei-templates/         # Nuclei vulnerability templates
/opt/security-tools/          # Tool runner scripts
├── tool-runner.py           # Main tool execution service
├── healthcheck.py           # Container health monitoring
├── resource-monitor.py      # Resource usage monitoring
└── network-validator.py     # Network access validation
/etc/mmcode-sandbox/         # Configuration files
├── nmap/                   # Nmap configurations
├── nuclei/                 # Nuclei configurations
└── iptables-rules.sh       # Network security rules
/tmp/scan-results/          # Output directory
├── logs/                   # Execution logs
└── [scan-outputs]          # Tool output files
```

### Security Features

#### Network Isolation
- Access restricted to private IP ranges (10.x, 172.16-31.x, 192.168.x)
- External internet access blocked
- Rate limiting on network connections
- Comprehensive connection logging

#### Resource Limits
- 2GB memory limit (soft), 2.5GB (hard)
- 2 CPU cores maximum
- 1-hour CPU time limit per process
- 512MB temporary filesystem
- File descriptor limits enforced

#### Process Security
- Non-root execution (UID 1001)
- Read-only root filesystem
- No new privileges flag set
- AppArmor security profile
- Limited process count (100/150)

#### Tool Restrictions
- Authorized tools whitelist
- Argument validation and filtering
- Dangerous operation blocking
- Template filtering for Nuclei
- Execution timeout enforcement

### Tool Configuration

#### Nmap
- Default configuration in `/etc/mmcode-sandbox/nmap/nmap.conf`
- Maximum parallelism: 50
- Scan delay: 1000ms
- Script filtering applied

#### Nuclei
- Templates from official repository
- Configuration in `/etc/mmcode-sandbox/nuclei/nuclei.yaml`
- Concurrency: 25 threads
- Rate limit: 150 requests/second
- Dangerous template categories blocked

#### Masscan
- High-speed scanning with rate limits
- Maximum rate: 5000 packets/second
- Proper privilege handling
- Output format restrictions

### Monitoring and Logging

#### Health Checks
- Tool availability verification
- Resource limit validation
- Network configuration checks
- File system security verification
- Process monitoring

#### Resource Monitoring
- Real-time CPU usage tracking
- Memory consumption monitoring
- I/O operation counting
- Process count tracking
- Alert thresholds configured

#### Audit Logging
- All tool executions logged
- Resource usage recorded
- Network access attempts logged
- Security violations tracked
- Structured JSON log format

### API Integration

The sandbox exposes a controlled API for tool execution:

```python
# Example tool execution request
{
    "tool_name": "nmap",
    "target": "192.168.1.100",
    "command_args": ["-sV", "-p", "80,443"],
    "options": {
        "output_format": "xml",
        "scan_type": "service_detection"
    },
    "timeout": 300,
    "session_id": "scan_session_001"
}
```

### Development and Testing

#### Local Testing
```bash
# Build and test locally
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Run health checks
docker-compose exec mmcode-sandbox python3 /opt/security-tools/healthcheck.py

# Check logs
docker-compose logs mmcode-sandbox

# Execute test scan
docker-compose exec mmcode-sandbox nmap -sV 192.168.1.1
```

#### Production Deployment
```bash
# Production deployment
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Monitor services
docker-compose exec network-monitor netstat -tulnp
docker-compose exec resource-monitor top

# Backup configurations
docker cp mmcode-security-sandbox:/etc/mmcode-sandbox ./config-backup
```

### Configuration Management

#### Environment Variables
- `MMCODE_SANDBOX_MODE`: production|development
- `MMCODE_LOG_LEVEL`: DEBUG|INFO|WARNING|ERROR
- `MMCODE_MAX_SCAN_TIME`: Maximum scan duration (seconds)
- `MMCODE_MAX_TARGETS`: Maximum number of targets per scan
- `MMCODE_ENABLE_MONITORING`: Enable resource monitoring

#### Volume Mounts
- `./results:/tmp/scan-results`: Scan results and logs
- `./configs:/etc/mmcode-sandbox:ro`: Configuration files
- `./scripts:/opt/security-tools:ro`: Tool scripts

#### Network Configuration
- `sandbox_network`: Isolated container network (172.20.0.0/24)
- `monitoring_network`: Monitoring services network (172.21.0.0/24)

### Troubleshooting

#### Common Issues

1. **Permission Denied Errors**
   ```bash
   # Check user permissions
   docker-compose exec mmcode-sandbox id
   
   # Verify volume permissions
   ls -la results/ configs/
   ```

2. **Network Access Issues**
   ```bash
   # Check iptables rules
   docker-compose exec mmcode-sandbox iptables -L -n
   
   # Test connectivity
   docker-compose exec mmcode-sandbox ping 192.168.1.1
   ```

3. **Resource Limits**
   ```bash
   # Check resource usage
   docker stats mmcode-security-sandbox
   
   # Review resource monitor logs
   docker-compose logs resource-monitor
   ```

4. **Tool Execution Failures**
   ```bash
   # Check tool availability
   docker-compose exec mmcode-sandbox which nmap nuclei
   
   # Test tool execution
   docker-compose exec mmcode-sandbox nmap --version
   docker-compose exec mmcode-sandbox nuclei -version
   ```

#### Log Analysis
```bash
# View all sandbox logs
docker-compose exec mmcode-sandbox find /tmp/scan-results/logs -name "*.log" -exec tail -n 20 {} +

# Monitor real-time logs
docker-compose logs -f mmcode-sandbox

# Check security events
docker-compose exec mmcode-sandbox grep "MMCODE-SANDBOX" /var/log/kern.log
```

### Security Considerations

1. **Network Isolation**: Ensure sandbox network doesn't have external access
2. **Resource Limits**: Monitor for resource exhaustion attacks
3. **Log Security**: Protect logs from unauthorized access
4. **Tool Updates**: Regularly update security tools and templates
5. **Configuration Management**: Secure configuration file permissions

### Maintenance

#### Regular Tasks
- Update Nuclei templates monthly
- Review and rotate logs weekly
- Security patch updates quarterly
- Performance monitoring daily
- Backup configurations weekly

#### Updates
```bash
# Update Nuclei templates
docker-compose exec mmcode-sandbox nuclei -update-templates

# Rebuild container with updates
docker-compose build --no-cache
docker-compose up -d
```

### Support

For issues and questions:
- Check logs: `/tmp/scan-results/logs/`
- Run health check: `/opt/security-tools/healthcheck.py`
- Review network rules: `/etc/mmcode-sandbox/iptables-rules.sh`
- Monitor resources: Resource monitoring dashboard