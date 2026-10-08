const API = "/api/v1";

export type Project = {
  id: number;
  name: string;
  description: string;
  repository_url: string | null;
  owner_id: number;
  created_at: string;
};

export type Environment = {
  id: number;
  name: string;
  project_id: number;
};

export type DeploymentHistory = {
  id: number;
  project_id: number;
  environment_id: number;
  repository_path: string;
  image_name: string;
  application_name: string;
  namespace: string;
  replicas: number;
  build_id: number;
  security_scan_id: number | null;
  deployment_id: number | null;
  status: string;
  build_status: string;
  validation_status: string;
  security_status: string;
  high_count: number;
  critical_count: number;
  message: string;
  created_at: string;
};

export type KubernetesDeployment = {
  id: number;
  project_id: number;
  environment_id: number | null;
  image_name: string;
  application_name: string;
  namespace: string;
  replicas: number;
  status: string;
  rollback_of_id: number | null;
  created_at: string;
};

export type SecurityFinding = {
  vulnerability_id: string | null;
  package: string | null;
  installed_version: string | null;
  fixed_version: string | null;
  severity: string;
  title: string | null;
  target: string | null;
};

export type SecurityScan = {
  id: number;
  project_id: number;
  build_id: number;
  image_name: string;
  status: string;
  unknown_count: number;
  low_count: number;
  medium_count: number;
  high_count: number;
  critical_count: number;
  findings: SecurityFinding[];
  created_at: string;
};

export type DeploymentRequest = {
  environment_id: number;
};

export type RepositoryAnalysis = {
  repository_url: string;
  languages: string[];
  frameworks: string[];
  has_dockerfile: boolean;
  has_ci: boolean;
  has_kubernetes: boolean;
  has_helm: boolean;
  has_tests: boolean;
  has_readme: boolean;
};

export type BuildPlan = {
  project_id: number;
  project_name: string;
  build_type: string;
  dockerfile_required: boolean;
  image_name: string;
  target_environment: string;
  steps: string[];
};

export type DeploymentResponse = {
  status: string;
  project_id: number;
  environment_id: number;
  image_name: string;
  build_id: number;
  security_scan_id: number | null;
  deployment_id: number | null;
  deployment_name: string | null;
  service_name: string | null;
  namespace: string;
  replicas: number;
  build_status: string;
  validation_status: string;
  security_status: string;
  high_count: number;
  critical_count: number;
  message: string;
};

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API}${path}`);

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail ?? `API request failed: ${response.status}`);
  }

  return data;
}

export type RollbackResponse = {
  status: string;
  project_id: number;
  environment_id: number;
  deployment_id: number;
  rollback_of_id: number;
  image_name: string;
  deployment_name: string;
  service_name: string;
  namespace: string;
  replicas: number;
  message: string;
};

export const api = {
  projects: () => get<Project[]>("/projects"),

  project: (projectId: number) =>
    get<Project>(`/projects/${projectId}`),

  environments: (projectId: number) =>
    get<Environment[]>(`/projects/${projectId}/environments`),

  deploymentHistory: (projectId: number) =>
    get<DeploymentHistory[]>(
      `/projects/${projectId}/deployment-history`,
    ),

  deployments: (projectId: number) =>
    get<KubernetesDeployment[]>(
      `/projects/${projectId}/deployments`,
    ),

    rollback: (projectId: number, deploymentId: number) =>
    post<RollbackResponse>(
      `/projects/${projectId}/deployments/${deploymentId}/rollback`,
      {},
    ),

  securityScans: (projectId: number) =>
    get<SecurityScan[]>(
      `/projects/${projectId}/security-scans`,
    ),

  importGithub: (repositoryUrl: string) =>
    post<Project>("/projects/import/github", {
      repository_url: repositoryUrl,
    }),

  analyzeRepository: (repositoryUrl: string) =>
    post<RepositoryAnalysis>("/repository/analyze", {
      repository_url: repositoryUrl,
    }),

  buildPlan: (projectId: number) =>
    post<BuildPlan>(`/projects/${projectId}/build-plan`, {}),

  deploy: (projectId: number, request: DeploymentRequest) =>
    post<DeploymentResponse>(
      `/projects/${projectId}/deploy-pipeline`,
      request,
    ),
};
