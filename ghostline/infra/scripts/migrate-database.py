#!/usr/bin/env python3
"""
Run database migration in the GhostLine VPC using ECS.
"""

import boto3
import json
import time
import sys

# AWS clients
ecs = boto3.client('ecs', region_name='us-west-2')
ec2 = boto3.client('ec2', region_name='us-west-2')
logs = boto3.client('logs', region_name='us-west-2')

def get_vpc_subnets():
    """Get private subnets from the VPC."""
    response = ec2.describe_subnets(
        Filters=[
            {'Name': 'vpc-id', 'Values': ['vpc-00d75267879c8f631']},
            {'Name': 'tag:Name', 'Values': ['*private*']}
        ]
    )
    return [subnet['SubnetId'] for subnet in response['Subnets']]

def get_security_group():
    """Get the ECS security group."""
    response = ec2.describe_security_groups(
        Filters=[
            {'Name': 'vpc-id', 'Values': ['vpc-00d75267879c8f631']},
            {'Name': 'tag:Name', 'Values': ['*ecs*']}
        ]
    )
    if response['SecurityGroups']:
        return response['SecurityGroups'][0]['GroupId']
    return None

def run_migration():
    """Run the database migration."""
    print("🚀 Starting database migration...")
    
    # Get network configuration
    subnets = get_vpc_subnets()
    security_group = get_security_group()
    
    if not subnets or not security_group:
        print("❌ Could not find network configuration")
        return False
    
    print(f"📍 Using subnets: {subnets}")
    print(f"🔒 Using security group: {security_group}")
    
    # Define the migration command
    migration_command = [
        "sh", "-c",
        """
        echo '🔍 Running database migration...' && \
        cd /app && \
        python -c "
import os
os.environ['DATABASE_URL'] = 'postgresql://ghostline:ghostline123!@ghostline-dev.cpygckmsmh2k.us-west-2.rds.amazonaws.com:5432/ghostline'

# First create pgvector extension
import psycopg2
conn = psycopg2.connect(os.environ['DATABASE_URL'])
conn.autocommit = True
cur = conn.cursor()
cur.execute('CREATE EXTENSION IF NOT EXISTS vector')
print('✅ pgvector extension created')
cur.close()
conn.close()

# Run Alembic migrations
import subprocess
result = subprocess.run(['alembic', 'upgrade', 'head'], capture_output=True, text=True)
print(result.stdout)
if result.returncode != 0:
    print('❌ Migration failed:', result.stderr)
    exit(1)
else:
    print('✅ Migrations completed successfully')
"
        """
    ]
    
    # Run the task
    try:
        response = ecs.run_task(
            cluster='ghostline-dev',
            taskDefinition='ghostline-dev-api:latest',
            launchType='FARGATE',
            networkConfiguration={
                'awsvpcConfiguration': {
                    'subnets': subnets[:2],  # Use first 2 subnets
                    'securityGroups': [security_group],
                    'assignPublicIp': 'DISABLED'
                }
            },
            overrides={
                'containerOverrides': [{
                    'name': 'api',
                    'command': migration_command
                }]
            }
        )
        
        if not response['tasks']:
            print("❌ Failed to start migration task")
            return False
        
        task_arn = response['tasks'][0]['taskArn']
        print(f"📋 Started migration task: {task_arn.split('/')[-1]}")
        
        # Wait for task to complete
        print("⏳ Waiting for migration to complete...")
        waiter = ecs.get_waiter('tasks_stopped')
        waiter.wait(
            cluster='ghostline-dev',
            tasks=[task_arn],
            WaiterConfig={'Delay': 5, 'MaxAttempts': 60}
        )
        
        # Get task result
        task_details = ecs.describe_tasks(
            cluster='ghostline-dev',
            tasks=[task_arn]
        )
        
        exit_code = task_details['tasks'][0]['containers'][0].get('exitCode', -1)
        
        # Get logs
        print("\n📋 Migration logs:")
        try:
            log_events = logs.get_log_events(
                logGroupName='/ecs/ghostline-dev',
                logStreamName=f"ecs/api/{task_arn.split('/')[-1]}",
                startFromHead=True
            )
            for event in log_events['events']:
                print(event['message'].rstrip())
        except Exception as e:
            print(f"Could not retrieve logs: {e}")
        
        if exit_code == 0:
            print("\n✅ Database migration completed successfully!")
            return True
        else:
            print(f"\n❌ Migration failed with exit code: {exit_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error running migration: {e}")
        return False

def verify_schema():
    """Verify the database schema was created."""
    print("\n🔍 Verifying database schema...")
    
    verification_command = [
        "python", "-c",
        """
import os
os.environ['DATABASE_URL'] = 'postgresql://ghostline:ghostline123!@ghostline-dev.cpygckmsmh2k.us-west-2.rds.amazonaws.com:5432/ghostline'

from sqlalchemy import create_engine, inspect
engine = create_engine(os.environ['DATABASE_URL'])
inspector = inspect(engine)
tables = sorted(inspector.get_table_names())
print(f'Found {len(tables)} tables:')
for table in tables:
    print(f'  ✅ {table}')
"""
    ]
    
    try:
        response = ecs.run_task(
            cluster='ghostline-dev',
            taskDefinition='ghostline-dev-api:latest',
            launchType='FARGATE',
            networkConfiguration={
                'awsvpcConfiguration': {
                    'subnets': get_vpc_subnets()[:2],
                    'securityGroups': [get_security_group()],
                    'assignPublicIp': 'DISABLED'
                }
            },
            overrides={
                'containerOverrides': [{
                    'name': 'api',
                    'command': verification_command
                }]
            }
        )
        
        task_arn = response['tasks'][0]['taskArn']
        print(f"📋 Running verification task: {task_arn.split('/')[-1]}")
        
        # Wait for completion
        waiter = ecs.get_waiter('tasks_stopped')
        waiter.wait(
            cluster='ghostline-dev',
            tasks=[task_arn],
            WaiterConfig={'Delay': 5, 'MaxAttempts': 30}
        )
        
        # Get logs
        time.sleep(5)  # Give logs time to appear
        try:
            log_events = logs.get_log_events(
                logGroupName='/ecs/ghostline-dev',
                logStreamName=f"ecs/api/{task_arn.split('/')[-1]}",
                startFromHead=True
            )
            for event in log_events['events']:
                print(event['message'].rstrip())
        except:
            pass
            
    except Exception as e:
        print(f"Could not verify schema: {e}")

if __name__ == "__main__":
    # Run migration
    if run_migration():
        # Verify if successful
        verify_schema()
        sys.exit(0)
    else:
        sys.exit(1) 