output "primary_endpoint" {
  description = "The primary endpoint of the Redis cluster"
  value       = aws_elasticache_cluster.main.cache_nodes[0].address
}

output "port" {
  description = "The port of the Redis cluster"
  value       = aws_elasticache_cluster.main.port
} 