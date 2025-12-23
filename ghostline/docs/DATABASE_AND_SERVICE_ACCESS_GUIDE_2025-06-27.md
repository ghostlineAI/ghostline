---
Last Updated: 2025-06-28 09:30:52 PDT
---

# GhostLine Infrastructure Access Guide

This document provides a comprehensive guide for developers to access and connect to the various infrastructure components of the GhostLine project, such as the PostgreSQL database and Redis cache.

## 1. Network Architecture Overview

**All backend services, including the database and cache, are deployed within a private VPC and are not directly accessible from the public internet.** This is a critical security measure.

To connect to these services from your local machine, you must use one of the access methods described below, which involve connecting through an intermediary resource that has access to the VPC.

## 2. PostgreSQL Database (AWS RDS)

The primary application database is a PostgreSQL instance running on AWS RDS.

### Connection Details
-   **Host**: `ghostline-dev.cpygckmsmh2k.us-west-2.rds.amazonaws.com`
-   **Port**: `5432`
-   **Database Name**: `ghostline`
-   **Username**: `ghostline`
-   **Password**: `ghostline123!`
-   **SSL Mode**: `require`

### Recommended Access Method: SSH Tunneling via Bastion Host

For connecting with a GUI-based database tool (like DBeaver, TablePlus, or pgAdmin), setting up an SSH tunnel through a bastion host is the most stable and secure method.

**Step 1: Set up a Bastion Host**
A bastion host is a small EC2 instance that lives in a public subnet of the VPC and is allowed to communicate with the private resources. You will need to launch one.
-   **Instance Type**: `t2.micro` or `t3.micro` is sufficient.
-   **AMI**: Amazon Linux 2 or Ubuntu.
-   **VPC**: Select the `ghostline-dev-vpc` (`vpc-00d75267879c8f631`).
-   **Subnet**: Select one of the **public** subnets.
-   **Security Group**: Create a new security group that allows SSH traffic (port 22) from your IP address.
-   **Key Pair**: Create and use a new key pair to access the instance.

**Step 2: Configure the SSH Tunnel**
Once the bastion is running, you can create an SSH tunnel from your local machine.

```bash
# Replace with your bastion's public IP and the path to your private key
ssh -i /path/to/your-key.pem -N -L 5433:ghostline-dev.cpygckmsmh2k.us-west-2.rds.amazonaws.com:5432 ec2-user@<BASTION_IP_ADDRESS>
```

-   `-i`: Path to your private SSH key.
-   `-N`: Do not execute a remote command.
-   `-L`: Binds a local port to a remote host and port. This command binds your local port `5433` to the RDS host on port `5432`.

**Step 3: Connect Your GUI Tool**
Now, configure your database client to connect to `localhost` on the local port you bound (`5433`).
-   **Host**: `localhost`
-   **Port**: `5433`
-   **Database**: `ghostline`
-   **Username**: `ghostline`
-   **Password**: `ghostline123!`
-   **SSL**: `require`

The SSH tunnel will securely forward the connection from your local machine to the RDS instance within the private VPC.

## 3. Redis Cache (AWS ElastiCache)

The application uses a Redis cluster for caching and background job queuing.

### Connection Details
-   **Host**: `ghostline-dev.xntopp.0001.usw2.cache.amazonaws.com`
-   **Port**: `6379`

### Access Method: SSH Tunneling via Bastion Host

Access to Redis uses the same SSH tunneling method as the database.

**Step 1: Create an SSH Tunnel**
You can add another `-L` flag to your existing SSH command or run a new one.

```bash
# Command with tunnels for both RDS and Redis
ssh -i /path/to/your-key.pem -N \
  -L 5433:ghostline-dev.cpygckmsmh2k.us-west-2.rds.amazonaws.com:5432 \
  -L 6380:ghostline-dev.xntopp.0001.usw2.cache.amazonaws.com:6379 \
  ec2-user@<BASTION_IP_ADDRESS>
```
This command binds your local port `6380` to the Redis host on port `6379`.

**Step 2: Connect with `redis-cli` or GUI**
You can now connect to Redis using a client pointed at your local machine.

```bash
# Connect using redis-cli
redis-cli -h localhost -p 6380
```

## 4. Production Credentials in AWS Secrets Manager

Note that the credentials provided here are for the `dev` environment. In a production environment, you should never hardcode credentials. The application retrieves its credentials securely from **AWS Secrets Manager**.

-   **RDS Secret Name**: `ghostline/dev/database-url`
-   **Redis Secret Name**: `ghostline/dev/redis-url`

You can view these secrets in the AWS Console or via the AWS CLI if you have the appropriate permissions.

---
*This guide should provide everything needed for developers to connect to the project's infrastructure. Please keep it updated if any details change.* 