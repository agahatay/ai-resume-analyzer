#!/bin/bash
# Paste this into Oracle Cloud > Create instance > Advanced options >
# Management > "Paste cloud-init script". Change DOMAIN first.
# Progress: ssh in and run  tail -f /var/log/ai-resume-setup.log
DOMAIN=CHANGE_ME.duckdns.org

apt-get update && apt-get install -y git
git clone https://github.com/agahatay/ai-resume-analyzer.git /opt/ai-resume-analyzer
DOMAIN=$DOMAIN bash /opt/ai-resume-analyzer/deploy/setup.sh > /var/log/ai-resume-setup.log 2>&1
