#!/bin/bash
# Install orchestrator update service as systemd timer

set -e

# Create systemd service file
sudo tee /etc/systemd/system/orchestrator-update.service > /dev/null <<EOF
[Unit]
Description=Orchestrator Cluster Full Update
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
ExecStart=/home/geo/operation/scripts/orchestrator_full_update.sh --auto
StandardOutput=journal
StandardError=journal
User=geo
Group=docker

[Install]
WantedBy=multi-user.target
EOF

# Create systemd timer file
sudo tee /etc/systemd/system/orchestrator-update.timer > /dev/null <<EOF
[Unit]
Description=Run Orchestrator Update every hour
Requires=orchestrator-update.service

[Timer]
# Run every hour
OnCalendar=hourly
# Run immediately if system was offline when timer should have triggered
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Make update script executable
chmod +x /home/geo/operation/scripts/orchestrator_full_update.sh

# Reload systemd
sudo systemctl daemon-reload

# Enable and start timer
sudo systemctl enable orchestrator-update.timer
sudo systemctl start orchestrator-update.timer

echo "Orchestrator update service installed!"
echo ""
echo "Commands:"
echo "  Check timer status:  systemctl status orchestrator-update.timer"
echo "  Check last run:      systemctl status orchestrator-update.service"
echo "  Run manually:        systemctl start orchestrator-update.service"
echo "  View logs:           journalctl -u orchestrator-update.service -f"
echo "  Disable updates:     systemctl stop orchestrator-update.timer"