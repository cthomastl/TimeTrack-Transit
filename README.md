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
- `POST /api/v1/departures` - Schedule a new departure
- `GET /api/v1/departures/{id}` - Get departure by ID
- `PUT /api/v1/departures/{id}` - Update departure
- `DELETE /api/v1/departures/{id}` - Delete departure
- `POST /api/v1/departures/{id}/record-departure` - Record actual departure time
- `POST /api/v1/departures/{id}/cancel` - Cancel departure

### Queries
- `GET /api/v1/departures?date=YYYY-MM-DD` - Get departures by date
- `GET /api/v1/departures/late?date=YYYY-MM-DD` - Get late departures
- `GET /api/v1/departures/route/{route_number}?date=YYYY-MM-DD` - Get by route

### Reports
- `GET /api/v1/reports/late-departures?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` - Late departure summary

## Local Development

### Prerequisites

- Python 3.11+
- AWS credentials (or DynamoDB Local)

### Setup

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

## License

Proprietary - Humble City Transit Authority
