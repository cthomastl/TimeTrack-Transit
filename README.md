# TimeTrack-Transit

Bus Departure Tracking System for Humble, TX City Buses.

## Overview

TimeTrack-Transit is a backend API service that tracks bus departures from the Humble Transit Station. It monitors scheduled vs. actual departure times, identifies late departures, and provides reporting capabilities.

## Features

- Schedule and track bus departures
- Record actual departure times
- Automatic late departure detection (>5 minutes delay)
- Query departures by date, route, or status
- Generate late departure summary reports
- DynamoDB integration for data persistence

## Tech Stack

- **Framework**: FastAPI
- **Database**: AWS DynamoDB
- **Runtime**: Python 3.11+
- **Deployment**: AWS EC2 (Private Subnet)

## API Endpoints

### Health
- `GET /` - API information
- `GET /health` - Health check

### Departures
- `POST /api/v1/log-departure` - **Simplified endpoint**: Log departure with automatic delay calculation
- `POST /api/v1/departures` - Schedule a new departure
- `GET /api/v1/departures/{id}` - Get departure by ID
- `PUT /api/v1/departures/{id}` - Update departure
- `DELETE /api/v1/departures/{id}` - Delete departure
- `POST /api/v1/departures/{id}/record-departure` - Record actual departure time
- `POST /api/v1/departures/{id}/cancel` - Cancel departure

### Log Departure (Simplified)

The `/api/v1/log-departure` endpoint provides a simple way to log departures:

```bash
curl -X POST http://localhost:8000/api/v1/log-departure \
  -H "Content-Type: application/json" \
  -d '{
    "bus_id": "BUS-101",
    "scheduled_time": "2026-02-03T08:00:00",
    "actual_time": "2026-02-03T08:07:00"
  }'
```

Response:
```json
{
  "departure_id": "uuid-here",
  "bus_id": "BUS-101",
  "scheduled_time": "2026-02-03T08:00:00",
  "actual_time": "2026-02-03T08:07:00",
  "delay_minutes": 7,
  "is_late": true,
  "message": "Bus BUS-101 departed 7 minutes late."
}
```

### Queries
- `GET /api/v1/departures?date=YYYY-MM-DD` - Get departures by date
- `GET /api/v1/departures/late?date=YYYY-MM-DD` - Get late departures
- `GET /api/v1/departures/route/{route_number}?date=YYYY-MM-DD` - Get by route

### Reports
- `GET /api/v1/reports/late-departures?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` - Late departure summary

## Local Development

### Prerequisites

- Python 3.14+ (or Docker)
- AWS credentials (or DynamoDB Local)

### Quick Start with Docker (Recommended)

The easiest way to run the complete application locally:

```bash
# Start all services (backend, frontend, DynamoDB-Local)
docker-compose up --build

# Access the application:
# - Frontend Dashboard: http://localhost
# - Backend API: http://localhost:8000
# - API Documentation: http://localhost:8000/docs
# - DynamoDB Local: http://localhost:8001
```

### Manual Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd TimeTrack-Transit
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

5. Run the application:
```bash
python -m app.main
# or
uvicorn app.main:app --reload
```

6. Access API docs at http://localhost:8000/docs

### Running Tests

```bash
pytest tests/ -v
```

## EC2 Deployment (Private Subnet)

### Prerequisites

- VPC with private subnet
- NAT Gateway for outbound internet access
- DynamoDB VPC Endpoint (recommended)

### Using CloudFormation

```bash
aws cloudformation create-stack \
  --stack-name timetrack-transit \
  --template-body file://deploy/cloudformation-template.yaml \
  --parameters \
    ParameterKey=VpcId,ParameterValue=<vpc-id> \
    ParameterKey=PrivateSubnetId,ParameterValue=<subnet-id> \
    ParameterKey=KeyPairName,ParameterValue=<key-pair> \
  --capabilities CAPABILITY_NAMED_IAM
```

### Manual Deployment

1. Launch EC2 in private subnet
2. Attach IAM role with DynamoDB permissions (see `deploy/iam-policy.json`)
3. Install application using `deploy/ec2-user-data.sh`
4. Configure systemd service (`deploy/timetrack-transit.service`)

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| AWS_REGION | AWS region | us-east-1 |
| DYNAMODB_TABLE_NAME | DynamoDB table | TimeTrack-Transit-DB |
| APP_HOST | API host | 0.0.0.0 |
| APP_PORT | API port | 8000 |
| LATE_THRESHOLD_MINUTES | Minutes before marked late | 5 |
| STATION_NAME | Station name | Humble Transit Station |
| STATION_TIMEZONE | Timezone | America/Chicago |

## DynamoDB Schema

The application uses a single-table design:

- **PK**: `DEPARTURE#{departure_id}`
- **SK**: `SCHEDULED#{scheduled_departure}`

### Global Secondary Indexes

- **DepartureDateIndex**: Query by date
- **StatusDateIndex**: Query by status and date
- **RouteDateIndex**: Query by route and date

## Frontend Deployment to AWS App Runner

Deploy the frontend as a Docker container to AWS App Runner for a fully managed, auto-scaling solution.

### Step 1: Set Your Backend API URL

Edit `frontend/index.html` line 220 to point to your backend:

```javascript
const API_BASE_URL = 'https://your-backend-api.us-east-1.awsapprunner.com/api/v1';
```

### Step 2: Create ECR Repository

```bash
# Set variables
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=us-east-1

# Create ECR repository
aws ecr create-repository \
  --repository-name timetrack-frontend \
  --region $AWS_REGION
```

### Step 3: Build and Push Docker Image

```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build the image
cd frontend
docker build -t timetrack-frontend .

# Tag for ECR
docker tag timetrack-frontend:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/timetrack-frontend:latest

# Push to ECR
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/timetrack-frontend:latest
```

### Step 4: Create App Runner Service

```bash
# Create App Runner access role for ECR (one-time setup)
aws iam create-role \
  --role-name AppRunnerECRAccessRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "build.apprunner.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam attach-role-policy \
  --role-name AppRunnerECRAccessRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess

# Create the App Runner service
aws apprunner create-service \
  --service-name timetrack-frontend \
  --source-configuration '{
    "AuthenticationConfiguration": {
      "AccessRoleArn": "arn:aws:iam::'$AWS_ACCOUNT_ID':role/AppRunnerECRAccessRole"
    },
    "AutoDeploymentsEnabled": true,
    "ImageRepository": {
      "ImageIdentifier": "'$AWS_ACCOUNT_ID'.dkr.ecr.'$AWS_REGION'.amazonaws.com/timetrack-frontend:latest",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {
        "Port": "80"
      }
    }
  }' \
  --instance-configuration '{
    "Cpu": "0.25 vCPU",
    "Memory": "0.5 GB"
  }'
```

### Step 5: Get Your App Runner URL

```bash
# Check service status and get URL
aws apprunner describe-service \
  --service-arn arn:aws:apprunner:$AWS_REGION:$AWS_ACCOUNT_ID:service/timetrack-frontend \
  --query 'Service.ServiceUrl' \
  --output text
```

Your frontend will be available at: `https://xxxxxxxx.us-east-1.awsapprunner.com`

### Updating the Frontend

After making changes, rebuild and push:

```bash
cd frontend
docker build -t timetrack-frontend .
docker tag timetrack-frontend:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/timetrack-frontend:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/timetrack-frontend:latest

# App Runner auto-deploys if AutoDeploymentsEnabled is true
# Or trigger manually:
aws apprunner start-deployment \
  --service-arn arn:aws:apprunner:$AWS_REGION:$AWS_ACCOUNT_ID:service/timetrack-frontend
```

### App Runner Pricing

- **Build**: $0.005 per build minute
- **Compute**: $0.064 per vCPU-hour, $0.007 per GB-hour
- **Automatic scale-to-zero**: No charge when idle (after provisioned instances setting)

For a static frontend with minimal traffic, expect ~$5-10/month.

## AWS Security: IAM Instance Profiles

### Why Use IAM Instance Profiles?

**Never hardcode AWS credentials** in your application code, environment variables, or configuration files. Instead, use IAM Instance Profiles to securely grant your EC2 instances the permissions they need.

### How IAM Instance Profiles Work

1. **IAM Role**: A role defines what AWS services and actions are permitted (e.g., DynamoDB read/write)
2. **Instance Profile**: A container that passes the IAM role to an EC2 instance
3. **Automatic Credentials**: AWS SDK (boto3) automatically retrieves temporary credentials from the EC2 metadata service

When your EC2 instance has an instance profile attached, the AWS SDK automatically:
- Retrieves temporary credentials from `http://169.254.169.254/latest/meta-data/iam/security-credentials/`
- Refreshes credentials before they expire
- Uses these credentials for all AWS API calls

### Setting Up IAM Instance Profile

#### 1. Create an IAM Policy for DynamoDB Access

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:DescribeTable",
        "dynamodb:CreateTable"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:YOUR_ACCOUNT_ID:table/TimeTrack-Transit-DB",
        "arn:aws:dynamodb:us-east-1:YOUR_ACCOUNT_ID:table/TimeTrack-Transit-DB/index/*"
      ]
    }
  ]
}
```

#### 2. Create an IAM Role

```bash
# Create the trust policy for EC2
cat > trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the IAM role
aws iam create-role \
  --role-name TimeTrack-Transit-EC2-Role \
  --assume-role-policy-document file://trust-policy.json

# Attach the DynamoDB policy (create it first or use inline)
aws iam put-role-policy \
  --role-name TimeTrack-Transit-EC2-Role \
  --policy-name DynamoDBAccess \
  --policy-document file://dynamodb-policy.json
```

#### 3. Create Instance Profile and Attach Role

```bash
# Create the instance profile
aws iam create-instance-profile \
  --instance-profile-name TimeTrack-Transit-Profile

# Add the role to the instance profile
aws iam add-role-to-instance-profile \
  --instance-profile-name TimeTrack-Transit-Profile \
  --role-name TimeTrack-Transit-EC2-Role
```

#### 4. Attach to EC2 Instance

**When launching a new instance:**
```bash
aws ec2 run-instances \
  --image-id ami-xxxxx \
  --instance-type t3.micro \
  --iam-instance-profile Name=TimeTrack-Transit-Profile \
  --subnet-id subnet-xxxxx \
  ...
```

**For an existing instance:**
```bash
aws ec2 associate-iam-instance-profile \
  --instance-id i-xxxxx \
  --iam-instance-profile Name=TimeTrack-Transit-Profile
```

### Application Configuration for Production

When deploying to EC2 with an instance profile, your `.env` file should NOT contain AWS credentials:

```bash
# .env for EC2 with Instance Profile
APP_ENV=production
AWS_REGION=us-east-1
DYNAMODB_TABLE_NAME=TimeTrack-Transit-DB
# NO AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY needed!
```

The boto3 SDK in the application automatically uses the instance profile credentials. The code in `app/database/dynamodb.py` is already configured to work with instance profiles:

```python
# When aws_access_key_id and aws_secret_access_key are not set,
# boto3 automatically uses the instance profile credentials
client_kwargs = {"region_name": settings.aws_region}

if settings.aws_access_key_id and settings.aws_secret_access_key:
    # Only used for local development
    client_kwargs["aws_access_key_id"] = settings.aws_access_key_id
    client_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
```

### Security Best Practices

1. **Principle of Least Privilege**: Only grant permissions the application actually needs
2. **Use Resource-Level Permissions**: Restrict access to specific tables, not `*`
3. **Enable CloudTrail**: Monitor API calls made by your application
4. **VPC Endpoints**: Use DynamoDB VPC endpoints to keep traffic within AWS network
5. **Regular Rotation**: Instance profile credentials are automatically rotated by AWS

### Verifying Instance Profile from EC2

```bash
# Check if instance has an IAM role attached
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/

# Get the current credentials (for debugging only)
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/TimeTrack-Transit-EC2-Role
```

## License

Proprietary - Humble City Transit Authority
