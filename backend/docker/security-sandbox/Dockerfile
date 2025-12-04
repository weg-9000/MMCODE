# MMCODE Security Tool Sandbox Environment
# ========================================
#
# Secure, isolated environment for running security testing tools
# - Network-isolated container with controlled egress
# - Resource-limited execution environment  
# - Pre-installed security tools (Nmap, Nuclei, etc.)
# - Non-root execution for enhanced security

FROM kalilinux/kali-rolling:latest

# Metadata
LABEL name="MMCODE Security Sandbox"
LABEL version="1.0.0"
LABEL description="Isolated security tool execution environment"
LABEL maintainer="MMCODE Security Team"

# Environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV SANDBOX_USER=mmcode-runner
ENV SANDBOX_UID=1001
ENV SANDBOX_GID=1001
ENV TOOLS_DIR=/opt/security-tools
ENV OUTPUT_DIR=/tmp/scan-results
ENV CONFIG_DIR=/etc/mmcode-sandbox

# Update package lists and install essential packages
RUN apt-get update && \
    apt-get install -y \
        # Core utilities
        curl \
        wget \
        git \
        ca-certificates \
        gnupg \
        lsb-release \
        # Network tools
        net-tools \
        dnsutils \
        iputils-ping \
        # Security tools
        nmap \
        masscan \
        # Build tools for additional installations
        build-essential \
        python3 \
        python3-pip \
        python3-venv \
        golang-go \
        # Process management
        supervisor \
        # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Nuclei
RUN cd /tmp && \
    wget -q https://github.com/projectdiscovery/nuclei/releases/latest/download/nuclei_3.1.0_linux_amd64.zip && \
    unzip nuclei_3.1.0_linux_amd64.zip && \
    mv nuclei /usr/local/bin/ && \
    chmod +x /usr/local/bin/nuclei && \
    rm -f nuclei_3.1.0_linux_amd64.zip

# Install OWASP ZAP CLI
RUN cd /tmp && \
    wget -q https://github.com/zaproxy/zaproxy/releases/download/v2.14.0/ZAP_2_14_0_unix.sh && \
    chmod +x ZAP_2_14_0_unix.sh && \
    ./ZAP_2_14_0_unix.sh -q -dir /opt/zaproxy && \
    ln -s /opt/zaproxy/zap.sh /usr/local/bin/zap && \
    rm -f ZAP_2_14_0_unix.sh

# Create sandbox user and directories
RUN groupadd -g ${SANDBOX_GID} ${SANDBOX_USER} && \
    useradd -u ${SANDBOX_UID} -g ${SANDBOX_GID} -m -s /bin/bash ${SANDBOX_USER} && \
    mkdir -p ${TOOLS_DIR} ${OUTPUT_DIR} ${CONFIG_DIR} && \
    chown -R ${SANDBOX_USER}:${SANDBOX_USER} ${TOOLS_DIR} ${OUTPUT_DIR}

# Install Nuclei templates with proper permissions
RUN mkdir -p /home/${SANDBOX_USER}/nuclei-templates && \
    git clone https://github.com/projectdiscovery/nuclei-templates.git /home/${SANDBOX_USER}/nuclei-templates && \
    chown -R ${SANDBOX_USER}:${SANDBOX_USER} /home/${SANDBOX_USER}/nuclei-templates

# Copy security tool configurations
COPY configs/nmap/ ${CONFIG_DIR}/nmap/
COPY configs/nuclei/ ${CONFIG_DIR}/nuclei/
COPY configs/masscan/ ${CONFIG_DIR}/masscan/

# Copy tool execution wrapper scripts
COPY scripts/tool-runner.py ${TOOLS_DIR}/
COPY scripts/resource-monitor.py ${TOOLS_DIR}/
COPY scripts/network-validator.py ${TOOLS_DIR}/

# Set proper permissions for configurations and scripts
RUN chown -R root:${SANDBOX_USER} ${CONFIG_DIR} && \
    chmod -R 750 ${CONFIG_DIR} && \
    chown -R ${SANDBOX_USER}:${SANDBOX_USER} ${TOOLS_DIR} && \
    chmod +x ${TOOLS_DIR}/*.py

# Copy supervisor configuration for process management
COPY configs/supervisor/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create tool-specific configuration files
RUN echo "# MMCODE Nmap Configuration" > ${CONFIG_DIR}/nmap/nmap.conf && \
    echo "max-scan-delay=1000" >> ${CONFIG_DIR}/nmap/nmap.conf && \
    echo "max-parallelism=50" >> ${CONFIG_DIR}/nmap/nmap.conf && \
    echo "# MMCODE Nuclei Configuration" > ${CONFIG_DIR}/nuclei/nuclei.yaml && \
    echo "templates-directory: /home/${SANDBOX_USER}/nuclei-templates" >> ${CONFIG_DIR}/nuclei/nuclei.yaml && \
    echo "output-directory: ${OUTPUT_DIR}" >> ${CONFIG_DIR}/nuclei/nuclei.yaml && \
    echo "concurrency: 25" >> ${CONFIG_DIR}/nuclei/nuclei.yaml && \
    echo "rate-limit: 150" >> ${CONFIG_DIR}/nuclei/nuclei.yaml

# Security hardening
RUN # Remove unnecessary packages and clean up
    apt-get autoremove -y && \
    apt-get autoclean && \
    # Remove package manager caches
    rm -rf /var/cache/apt/* && \
    # Disable root login
    passwd -l root && \
    # Remove shell history
    rm -f /root/.bash_history && \
    # Set secure file permissions
    chmod 700 /home/${SANDBOX_USER} && \
    # Remove write permissions from system directories
    chmod -w /usr/bin /usr/sbin /bin /sbin

# Resource limits configuration
COPY configs/limits.conf /etc/security/limits.d/sandbox.conf

# Network security configuration
COPY configs/iptables-rules.sh ${CONFIG_DIR}/
RUN chmod +x ${CONFIG_DIR}/iptables-rules.sh

# Health check script
COPY scripts/healthcheck.py ${TOOLS_DIR}/
RUN chmod +x ${TOOLS_DIR}/healthcheck.py

# Switch to sandbox user
USER ${SANDBOX_USER}
WORKDIR /home/${SANDBOX_USER}

# Environment setup for sandbox user
ENV PATH="${TOOLS_DIR}:${PATH}"
ENV NUCLEI_TEMPLATES_DIR="/home/${SANDBOX_USER}/nuclei-templates"

# Expose required ports (none by default for security)
# EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 ${TOOLS_DIR}/healthcheck.py

# Default command
CMD ["python3", "/opt/security-tools/tool-runner.py"]

# Security labels
LABEL security.scan="enabled"
LABEL security.network="isolated"
LABEL security.user="non-root"
LABEL security.resources="limited"