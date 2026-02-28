export const CATEGORY_COLORS: Record<string, string> = {
  compute: "#10b981",
  database: "#8b5cf6",
  storage: "#6366f1",
  network: "#3b82f6",
  security: "#ef4444",
  serverless: "#f59e0b",
  cache: "#8b5cf6",
  queue: "#f97316",
  cdn: "#3b82f6",
  monitoring: "#06b6d4",
  ml: "#ec4899",
  analytics: "#a855f7",
};

export const SERVICE_CATEGORY: Record<string, string> = {
  ec2: "compute", ecs: "compute", eks: "compute", compute_engine: "compute",
  virtual_machines: "compute", emr: "compute",
  rds: "database", aurora: "database", dynamodb: "database", cloud_sql: "database",
  azure_sql: "database", cosmos_db: "database", redshift: "database", bigquery: "database",
  s3: "storage", cloud_storage: "storage", blob_storage: "storage", ebs: "storage", ecr: "storage",
  alb: "network", nlb: "network", route53: "network", cloud_load_balancing: "network",
  app_gateway: "network",
  cloudfront: "cdn", cloud_cdn: "cdn",
  waf: "security", cognito: "security", kms: "security", cloudtrail: "security", guardduty: "security",
  lambda: "serverless", api_gateway: "serverless", cloud_functions: "serverless", cloud_run: "serverless",
  azure_functions: "serverless", step_functions: "serverless", glue: "serverless",
  elasticache: "cache", memorystore: "cache", azure_cache: "cache",
  sqs: "queue", sns: "queue", pub_sub: "queue", service_bus: "queue", kinesis: "queue",
  cloudwatch: "monitoring",
  sagemaker: "ml",
};

// ASCII char per category — displayed inside the icon badge on each node
export const SERVICE_ICON_CHAR: Record<string, string> = {
  compute: "C", database: "D", storage: "S", network: "N",
  security: "K", serverless: "L", cache: "X", queue: "Q",
  cdn: "W", monitoring: "M", ml: "A", analytics: "B",
};

export function getServiceCategory(service: string): string {
  return SERVICE_CATEGORY[service] || "compute";
}

export function getCategoryColor(category: string): string {
  return CATEGORY_COLORS[category] || "#94a3b8";
}

export function getIconChar(service: string): string {
  const cat = getServiceCategory(service);
  return SERVICE_ICON_CHAR[cat] || "?";
}
