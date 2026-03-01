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
  containers: "#14b8a6",
  streaming: "#f97316",
  orchestration: "#a78bfa",
};

export const SERVICE_CATEGORY: Record<string, string> = {
  // AWS compute
  ec2: "compute", ecs: "compute", eks: "compute", emr: "compute",
  fargate: "compute", codepipeline: "compute", codecommit: "storage",
  codebuild: "compute", dms: "compute", migration_hub: "compute",
  // GCP compute
  compute_engine: "compute", gke: "containers", app_engine: "serverless",
  cloud_build: "compute",
  // Azure compute
  virtual_machines: "compute", aks: "containers", container_apps: "containers",
  azure_devops: "compute", azure_migrate: "compute",

  // Databases
  rds: "database", aurora: "database", dynamodb: "database", cloud_sql: "database",
  azure_sql: "database", cosmos_db: "database", redshift: "database", bigquery: "database",
  firestore: "database", spanner: "database", alloydb: "database",

  // Storage
  s3: "storage", cloud_storage: "storage", blob_storage: "storage", ebs: "storage",
  ecr: "storage", fsx: "storage", efs: "storage", artifact_registry: "storage",

  // Network
  alb: "network", nlb: "network", route53: "network", cloud_load_balancing: "network",
  app_gateway: "network", cloud_dns: "network", direct_connect: "network", vpn: "network",
  azure_lb: "network", azure_dns: "network", cloud_interconnect: "network",
  api_management: "network",

  // CDN
  cloudfront: "cdn", cloud_cdn: "cdn", azure_cdn: "cdn",

  // Security
  waf: "security", cognito: "security", kms: "security", cloudtrail: "security",
  guardduty: "security", shield: "security", security_hub: "security",
  config: "security", inspector: "security", cloud_armor: "security",
  firebase_auth: "security", azure_waf: "security", azure_ad: "security",
  azure_firewall: "security", azure_sentinel: "security", azure_policy: "security",

  // Serverless
  lambda: "serverless", api_gateway: "serverless", cloud_functions: "serverless",
  cloud_run: "serverless", azure_functions: "serverless", step_functions: "serverless",
  glue: "serverless", app_service: "serverless",

  // Cache
  elasticache: "cache", memorystore: "cache", azure_cache: "cache",

  // Queue
  sqs: "queue", sns: "queue", pub_sub: "queue", service_bus: "queue", kinesis: "queue",
  eventbridge: "queue",

  // Monitoring
  cloudwatch: "monitoring", cloud_logging: "monitoring", azure_monitor: "monitoring",

  // ML
  sagemaker: "ml", vertex_ai: "ml", azure_ml: "ml",

  // Analytics
  athena: "analytics", dataproc: "analytics", data_factory: "analytics", synapse: "analytics",

  // Streaming
  dataflow: "streaming", event_hubs: "streaming",

  // Orchestration
  cloud_composer: "orchestration", logic_apps: "orchestration",
};

// SVG path data per category (viewBox 0 0 24 24, stroke-based)
export const CATEGORY_ICONS: Record<string, string> = {
  compute: "M5 12H3l9-9 9 9h-2M5 12v7a2 2 0 002 2h10a2 2 0 002-2v-7",
  database: "M12 2C6.48 2 2 4.24 2 7v10c0 2.76 4.48 5 10 5s10-2.24 10-5V7c0-2.76-4.48-5-10-5zM2 12c0 2.76 4.48 5 10 5s10-2.24 10-5",
  storage: "M20 7H4a1 1 0 00-1 1v8a1 1 0 001 1h16a1 1 0 001-1V8a1 1 0 00-1-1zM4 12h16",
  network: "M12 2a10 10 0 100 20 10 10 0 000-20zm0 0a14.5 14.5 0 014 10 14.5 14.5 0 01-4 10 14.5 14.5 0 01-4-10A14.5 14.5 0 0112 2zM2 12h20",
  security: "M12 2l7 4v5c0 5.25-3.5 10.74-7 12-3.5-1.26-7-6.75-7-12V6l7-4z",
  serverless: "M13 2L3 14h9l-1 8 10-12h-9l1-8z",
  cache: "M4 4h16v4H4zM4 10h16v4H4zM4 16h16v4H4z",
  queue: "M4 6h16M4 12h16M4 18h16",
  cdn: "M12 2a10 10 0 100 20 10 10 0 000-20zm-1 17.93A8 8 0 013 12a8 8 0 018-7.93M12 2v20M2 12h20M4.22 7h15.56M4.22 17h15.56",
  monitoring: "M3 3v18h18M7 16l4-8 4 4 4-6",
  ml: "M12 2a4 4 0 014 4c0 1.95-1.4 3.57-3.24 3.9L12 14l-.76-4.1A4 4 0 018 6a4 4 0 014-4zM8 14h8M6 18h12M9 22h6",
  analytics: "M18 20V10M12 20V4M6 20v-6",
  containers: "M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16zM3.27 6.96L12 12l8.73-5.04M12 22.08V12",
  streaming: "M2 12c2-3 4-3 6 0s4 3 6 0 4-3 6 0 4 3 6 0",
  orchestration: "M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83",
};

export function getServiceCategory(service: string): string {
  return SERVICE_CATEGORY[service] || "compute";
}

export function getCategoryColor(category: string): string {
  return CATEGORY_COLORS[category] || "#94a3b8";
}

export function getCategoryIconPath(category: string): string {
  return CATEGORY_ICONS[category] || CATEGORY_ICONS["compute"];
}
