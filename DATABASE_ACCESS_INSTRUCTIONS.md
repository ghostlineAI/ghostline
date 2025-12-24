---
Last Updated: 2025-06-28 09:29:55 PDT
---

# GhostLine Database Access Instructions

## Overview

This guide covers how to access and manage the databases in the GhostLine AWS infrastructure.

## Databases Available

### 1. PostgreSQL (Main Database)
- **Purpose**: Stores all application data (users, projects, source materials, etc.)
- **Instance**: `ghostline-dev`
- **Endpoint**: `ghostline-dev.cpygckmsmh2k.us-west-2.rds.amazonaws.com`
- **Port**: 5432
- **Database Name**: `ghostline`
- **Username**: `ghostlineadmin`
- **Password**: `YO,_9~5]Vp}vrNGl`

### 2. Redis (Cache & Queue)
- **Purpose**: Used by Celery for task queuing and caching
- **Cluster**: `ghostline-dev`
- **Endpoint**: `ghostline-dev.xntopp.0001.usw2.cache.amazonaws.com`
- **Port**: 6379

### 3. DynamoDB (Terraform State Locking)
- **Table**: `ghostline-terraform-locks`
- **Purpose**: Prevents concurrent Terraform operations

## Prerequisites

1. **AWS CLI** installed and configured
2. **PostgreSQL client** (`psql`) installed
3. **SSH key** for jump host: `~/.ssh/ghostline-jump-key.pem`
4. **Jump host** running (instance: `i-0b166378578083427`)

## Quick Start

### Using the Database Connection Script

We've created a convenient script `db_connect.sh` for easy database access:

```bash
# Check connection status
./db_connect.sh status

# Start SSH tunnel
./db_connect.sh tunnel

# Connect to PostgreSQL
./db_connect.sh connect

# Show pgAdmin setup info
./db_connect.sh pgadmin

# Stop jump host (save money)
./db_connect.sh stop

# Start jump host
./db_connect.sh start
```

## Manual Connection Methods

### Method 1: Command Line (psql)

1. **Start the SSH tunnel**:
   ```bash
   ssh -N -L 5433:ghostline-dev.cpygckmsmh2k.us-west-2.rds.amazonaws.com:5432 \
       ec2-user@18.236.96.88 -i ~/.ssh/ghostline-jump-key.pem
   ```

2. **Connect to PostgreSQL** (in another terminal):
   ```bash
   PGPASSWORD='YO,_9~5]Vp}vrNGl' psql -h localhost -p 5433 -U ghostlineadmin -d ghostline
   ```

### Method 2: pgAdmin

1. **Option A - Manual SSH Tunnel**:
   - First run: `./db_connect.sh tunnel`
   - In pgAdmin:
     - Host: `localhost`
     - Port: `5433`
     - Database: `ghostline`
     - Username: `ghostlineadmin`
     - Password: `YO,_9~5]Vp}vrNGl`

2. **Option B - pgAdmin's Built-in SSH Tunnel**:
   - Connection tab:
     - Host: `ghostline-dev.cpygckmsmh2k.us-west-2.rds.amazonaws.com`
     - Port: `5432`
     - Database: `ghostline`
     - Username: `ghostlineadmin`
     - Password: `YO,_9~5]Vp}vrNGl`
   - SSH Tunnel tab:
     - Use SSH tunneling: ✓
     - Tunnel host: `18.236.96.88`
     - Tunnel port: `22`
     - Username: `ec2-user`
     - Identity file: `~/.ssh/ghostline-jump-key.pem`

### Method 3: TablePlus (Recommended for Mac)

1. Create new connection → PostgreSQL
2. Configure:
   - Name: `GhostLine Dev`
   - Host: `localhost`
   - Port: `5433`
   - User: `ghostlineadmin`
   - Password: `YO,_9~5]Vp}vrNGl`
   - Database: `ghostline`
3. Enable SSH:
   - SSH Host: `18.236.96.88`
   - SSH User: `ec2-user`
   - SSH Key: `~/.ssh/ghostline-jump-key.pem`

## Redis Access

To access Redis through the tunnel:

1. **Start tunnel with Redis forwarding**:
   ```bash
   ssh -N -L 5433:ghostline-dev.cpygckmsmh2k.us-west-2.rds.amazonaws.com:5432 \
       -L 6379:ghostline-dev.xntopp.0001.usw2.cache.amazonaws.com:6379 \
       ec2-user@18.236.96.88 -i ~/.ssh/ghostline-jump-key.pem
   ```

2. **Connect to Redis**:
   ```bash
   redis-cli -h localhost -p 6379
   ```

## SSH Configuration

Your `~/.ssh/config` should contain:

```ssh
# GhostLine Jump Host for Database Access
Host ghostline-db
    HostName 18.236.96.88
    User ec2-user
    IdentityFile ~/.ssh/ghostline-jump-key.pem
    LocalForward 5433 ghostline-dev.cpygckmsmh2k.us-west-2.rds.amazonaws.com:5432
    ServerAliveInterval 60
    ServerAliveCountMax 3
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null

# Alias for both PostgreSQL and Redis
Host ghostline-tunnel
    HostName 18.236.96.88
    User ec2-user
    IdentityFile ~/.ssh/ghostline-jump-key.pem
    LocalForward 5433 ghostline-dev.cpygckmsmh2k.us-west-2.rds.amazonaws.com:5432
    LocalForward 6379 ghostline-dev.xntopp.0001.usw2.cache.amazonaws.com:6379
    ServerAliveInterval 60
    ServerAliveCountMax 3
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
```

## Common Database Operations

### Check Database Schema
```sql
-- List all tables
\dt

-- Describe a table
\d users
\d projects
\d source_materials

-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Run Migrations
```bash
# From the API repository
cd ghostline/api
alembic upgrade head
```

### Backup Database
```bash
# Create backup
pg_dump -h localhost -p 5433 -U ghostlineadmin -d ghostline > ghostline_backup_$(date +%Y%m%d).sql

# Restore backup
psql -h localhost -p 5433 -U ghostlineadmin -d ghostline < ghostline_backup_20240628.sql
```

## Cost Management

### Jump Host Management
The EC2 jump host costs ~$8/month if running 24/7. To save money:

```bash
# Stop when not in use
./db_connect.sh stop
# or
aws ec2 stop-instances --instance-ids i-0b166378578083427

# Start when needed
./db_connect.sh start
# or
aws ec2 start-instances --instance-ids i-0b166378578083427
```

### Database Costs
- PostgreSQL RDS (db.t3.micro): ~$15-20/month
- Redis ElastiCache (cache.t3.micro): ~$12-15/month
- DynamoDB: Minimal (only for Terraform locks)

## Troubleshooting

### SSH Connection Times Out
```bash
# Check if jump host is running
aws ec2 describe-instances --instance-ids i-0b166378578083427 \
    --query 'Reservations[0].Instances[0].State.Name' --output text

# If stopped, start it
aws ec2 start-instances --instance-ids i-0b166378578083427
```

### Port Already in Use
```bash
# Check what's using port 5433
lsof -i :5433

# Kill existing SSH tunnel
kill $(lsof -ti :5433)
```

### Authentication Failed
- Verify password: `YO,_9~5]Vp}vrNGl` (note the underscore after comma)
- Check username: `ghostlineadmin` (all lowercase)

### Cannot Connect to Database
1. Ensure jump host is running
2. Check security group allows connection
3. Verify SSH tunnel is active: `lsof -i :5433`

## Connection Strings for Development

### PostgreSQL
```bash
# Through SSH tunnel
postgresql://ghostlineadmin:YO,_9~5]Vp}vrNGl@localhost:5433/ghostline

# Direct (only from within VPC)
postgresql://ghostlineadmin:YO,_9~5]Vp}vrNGl@ghostline-dev.cpygckmsmh2k.us-west-2.rds.amazonaws.com:5432/ghostline
```

### Redis
```bash
# Through SSH tunnel
redis://localhost:6379

# Direct (only from within VPC)
redis://ghostline-dev.xntopp.0001.usw2.cache.amazonaws.com:6379
```

## Security Notes

1. **Never commit credentials** to git repositories
2. **Use AWS Secrets Manager** for production applications
3. **Rotate passwords** regularly
4. **Limit jump host access** to specific IPs when possible
5. **Stop jump host** when not in use to reduce attack surface

## Support

For issues or questions:
1. Check CloudWatch logs for RDS/ElastiCache
2. Review security group configurations
3. Verify network connectivity from jump host
4. Check AWS service health dashboard 