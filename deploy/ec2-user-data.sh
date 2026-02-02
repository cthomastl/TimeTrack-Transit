#!/bin/bash
# EC2 User Data Script for TimeTrack-Transit
# This script runs on first boot to set up the application

set -e

# Update system packages
yum update -y

# Install Python 3.11 and dependencies
yum install -y python3.11 python3.11-pip git

# Create application user
useradd -r -s /bin/false timetrack || true

# Create application directory
mkdir -p /opt/timetrack-transit
cd /opt/timetrack-transit

# Clone or copy application (adjust as needed for your deployment method)
# For S3-based deployment:
# aws s3 cp s3://your-bucket/timetrack-transit.tar.gz .
# tar -xzf timetrack-transit.tar.gz

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Set permissions
chown -R timetrack:timetrack /opt/timetrack-transit

# Create environment file (will be populated via Parameter Store or Secrets Manager)
cat > /opt/timetrack-transit/.env << 'EOF'
AWS_REGION=us-east-1
DYNAMODB_TABLE_NAME=TimeTrack-Transit-DB
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO
STATION_NAME=Humble Transit Station
STATION_TIMEZONE=America/Chicago
EOF

# Set up systemd service
cp /opt/timetrack-transit/deploy/timetrack-transit.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable timetrack-transit
systemctl start timetrack-transit

echo "TimeTrack-Transit deployment complete"
