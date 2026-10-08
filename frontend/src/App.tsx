import { useEffect, useState } from "react";
import ImportRepository from "./pages/ImportRepository";
import {
  Activity,
  ArrowLeft,
  Boxes,
  CheckCircle2,
  Cloud,
  ExternalLink,
  LayoutDashboard,
  Rocket,
  Server,
  ShieldAlert,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import {
  NavLink,
  Route,
  Routes,
  useNavigate,
  useParams,
} from "react-router-dom";

import { api } from "./services/api";
import type {
  DeploymentHistory,
  DeploymentResponse,
  Environment,
  KubernetesDeployment,
  Project,
  SecurityScan,
} from "./services/api";

const DEFAULT_PROJECT_ID = 1;

function Loading() {
  return <div className="loading">Loading NEXUS data...</div>;
}

function ErrorBox({ message }: { message: string }) {
  return <div className="error-box">{message}</div>;
}

function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase();

  const type =
    normalized === "success" ||
    normalized === "running" ||
    normalized === "valid" ||
    normalized === "ready"
      ? "success"
      : normalized === "blocked" ||
        normalized === "failed"
        ? "danger"
        : "neutral";

  return <span className={`badge ${type}`}>{status}</span>;
}

function PipelineStep({
  label,
  status,
}: {
  label: string;
  status: string;
}) {
  const success = status === "success" || status === "valid";

  return (
    <div className="pipeline-step">
      {success ? (
        <CheckCircle2 className="success-icon" size={20} />
      ) : (
        <XCircle className="danger-icon" size={20} />
      )}

      <div>
        <strong>{label}</strong>
        <span>{status}</span>
      </div>
    </div>
  );
}

function SecurityMetric({
  label,
  value,
  danger = false,
}: {
  label: string;
  value: number;
  danger?: boolean;
}) {
  return (
    <div className="security-metric">
      <span>{label}</span>
      <strong className={danger && value > 0 ? "danger-text" : ""}>
        {value}
      </strong>
    </div>
  );
}

function HistoryTable({ rows }: { rows: DeploymentHistory[] }) {
  const [environmentNames, setEnvironmentNames] = useState<
    Record<number, string>
  >({});

  useEffect(() => {
    if (!rows.length) return;

    const projectIds = [...new Set(rows.map((row) => row.project_id))];

    Promise.all(
      projectIds.map(async (projectId) => {
        const environments = await api.environments(projectId);

        return environments.map((environment) => [
          environment.id,
          environment.name,
        ] as const);
      }),
    )
      .then((results) => {
        const mapping: Record<number, string> = {};

        results.flat().forEach(([id, name]) => {
          mapping[id] =
            name.charAt(0).toUpperCase() + name.slice(1);
        });

        setEnvironmentNames(mapping);
      })
      .catch(() => {
        // Keep fallback labels if environment lookup fails.
      });
  }, [rows]);

  if (!rows.length) {
    return <p className="muted">No deployment history.</p>;
  }

  return (
    <div className="pipeline-history">
      {rows.map((row) => {
        const environment =
          environmentNames[row.environment_id] ??
          `Environment #${row.environment_id}`;

        const deployed = Boolean(row.deployment_id);
        const protectedRun = row.status === "blocked";

        return (
          <div className="pipeline-run-card" key={row.id}>
            <div className="pipeline-run-header">
              <div>
                <div className="pipeline-run-title">
                  <Rocket size={16} />
                  <strong>{environment}</strong>
                  <span className="pipeline-run-id">
                    Pipeline #{row.id}
                  </span>
                </div>

                <div className="pipeline-run-meta">
                  Build #{row.build_id}
                  {row.security_scan_id
                    ? ` · Scan #${row.security_scan_id}`
                    : ""}
                  {" · "}
                  {new Date(row.created_at).toLocaleString()}
                </div>
              </div>

              <StatusBadge status={row.status} />
            </div>

            <div className="pipeline-run-steps">
              <div className="pipeline-run-step">
                <CheckCircle2 size={17} />
                <span>Build</span>
                <StatusBadge status={row.build_status} />
              </div>

              <div className="pipeline-run-step">
                <CheckCircle2 size={17} />
                <span>Validation</span>
                <StatusBadge status={row.validation_status} />
              </div>

              <div className="pipeline-run-step">
                {row.security_status === "blocked" ? (
                  <ShieldAlert size={17} />
                ) : (
                  <ShieldCheck size={17} />
                )}

                <span>Security</span>
                <StatusBadge status={row.security_status} />
              </div>

              <div className="pipeline-run-step">
                {deployed ? (
                  <CheckCircle2 size={17} />
                ) : (
                  <XCircle size={17} />
                )}

                <span>Deployment</span>
                <StatusBadge
                  status={deployed ? "success" : "not released"}
                />
              </div>
            </div>

            {(row.high_count > 0 || row.critical_count > 0) && (
              <div className="pipeline-security-summary">
                <ShieldAlert size={15} />

                
              </div>
            )}

            <div className="pipeline-run-footer">
              <span className="pipeline-run-message">
                {row.message}
              </span>

              {protectedRun && !deployed && (
                <span className="pipeline-protected-label">
                  Deployment protected · Nothing was released
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ---------------- Dashboard ---------------- */

function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [history, setHistory] = useState<DeploymentHistory[]>([]);
  const [scans, setScans] = useState<SecurityScan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadDashboard() {
      try {
        const projectList = await api.projects();

        const results = await Promise.all(
          projectList.map(async (project) => {
            const [envs, runs, security] = await Promise.all([
              api.environments(project.id),
              api.deploymentHistory(project.id),
              api.securityScans(project.id),
            ]);

            return {
              envs,
              runs,
              security,
            };
          }),
        );

        setProjects(projectList);

        setEnvironments(
          results.flatMap((result) => result.envs),
        );

        setHistory(
          results
            .flatMap((result) => result.runs)
            .sort(
              (a, b) =>
                new Date(b.created_at).getTime() -
                new Date(a.created_at).getTime(),
            ),
        );

        setScans(
          results
            .flatMap((result) => result.security)
            .sort(
              (a, b) =>
                new Date(b.created_at).getTime() -
                new Date(a.created_at).getTime(),
            ),
        );
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Failed to load dashboard",
        );
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, []);

  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} />;

  const latest = history[0];
  const latestScan = scans[0];

  const latestProject = latest
    ? projects.find((project) => project.id === latest.project_id)
    : null;

  const blockedRuns = history.filter(
    (run) => run.status === "blocked",
  ).length;

  const successfulRuns = history.filter(
    (run) => run.status === "success",
  ).length;

  return (
    <>
      <div className="page-heading">
        <div>
          <h1>NEXUS Dashboard</h1>
          <p className="muted">
            Build, deploy, monitor and learn from one platform.
          </p>
        </div>
      </div>

      <div className="stats">
        <div className="card stat-card">
          <span>Projects</span>
          <strong>{projects.length}</strong>
          <small>Projects registered in NEXUS</small>
        </div>

        <div className="card stat-card">
          <span>Environments</span>
          <strong>{environments.length}</strong>
          <small>Development and staging targets</small>
        </div>

        <div className="card stat-card">
          <span>Pipeline Runs</span>
          <strong>{history.length}</strong>
          <small>
            {successfulRuns} successful · {blockedRuns} protected
          </small>
        </div>

        <div className="card stat-card">
          <span>Security Gate</span>

          <strong
            className={
              latestScan?.status === "blocked"
                ? "danger-text"
                : ""
            }
          >
            {latestScan?.status ?? "—"}
          </strong>

          <small>
            {latestScan
              ? `${latestScan.high_count} HIGH / ${latestScan.critical_count} CRITICAL`
              : "No security scans yet"}
          </small>
        </div>
      </div>

      <div className="grid-two">
        <div className="card">
          <div className="card-header">
            <div>
              <h2>Latest Pipeline</h2>

              <p className="muted">
                {latestProject
                  ? latestProject.name
                  : "No pipeline activity yet"}
              </p>
            </div>

            {latest && (
              <StatusBadge status={latest.status} />
            )}
          </div>

          {latest ? (
            <>
              <div className="pipeline">
                <PipelineStep
                  label="Build"
                  status={latest.build_status}
                />

                <PipelineStep
                  label="Validation"
                  status={latest.validation_status}
                />

                <PipelineStep
                  label="Security"
                  status={latest.security_status}
                />

                <PipelineStep
                  label="Deployment"
                  status={
                    latest.deployment_id
                      ? "success"
                      : "blocked"
                  }
                />
              </div>

              {latest.status === "blocked" && (
                <div className="security-warning">
                  <ShieldAlert size={18} />

                  <div>
                    <strong>
                      Deployment protected
                    </strong>

                    <span>
                      NEXUS stopped this deployment because
                      security issues were detected.
                    </span>
                  </div>
                </div>
              )}
            </>
          ) : (
            <p className="muted">
              No deployment pipelines have been run yet.
            </p>
          )}
        </div>

        <div className="card">
          <div className="card-header">
            <div>
              <h2>Security Overview</h2>

              <p className="muted">
                Latest security scan across your projects
              </p>
            </div>

            <ShieldCheck size={22} />
          </div>

          {latestScan ? (
            <div className="security-grid">
              <SecurityMetric
                label="Critical"
                value={latestScan.critical_count}
                danger
              />

              <SecurityMetric
                label="High"
                value={latestScan.high_count}
                danger
              />

              <SecurityMetric
                label="Medium"
                value={latestScan.medium_count}
              />

              <SecurityMetric
                label="Low"
                value={latestScan.low_count}
              />
            </div>
          ) : (
            <p className="muted">
              No security scans available yet.
            </p>
          )}
        </div>
      </div>

      <div className="card large">
        <div className="card-header">
          <div>
            <h2>Recent Pipeline Activity</h2>

            <p className="muted">
              Latest activity across all NEXUS projects
            </p>
          </div>

          <Rocket size={20} />
        </div>

        <HistoryTable rows={history.slice(0, 5)} />
      </div>
    </>
  );
}

/* ---------------- Projects ---------------- */

function Projects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.projects()
      .then(setProjects)
      .finally(() => setLoading(false));
  }, []);

  const filtered = projects.filter((project) =>
    `${project.name} ${project.description ?? ""}`
      .toLowerCase()
      .includes(search.toLowerCase()),
  );

  if (loading) return <Loading />;

  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Projects</h1>
          <p className="muted">
            Projects registered in the NEXUS control plane.
          </p>
        </div>
      </div>

      <input
        className="search"
        placeholder="Search projects..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      <div className="project-grid">
        {filtered.map((project) => (
          <button
            className="project-card card project-button"
            key={project.id}
            onClick={() => navigate(`/projects/${project.id}`)}
          >
            <div className="project-icon">
              <Boxes size={20} />
            </div>

            <h2>{project.name}</h2>
            <p className="muted">{project.description}</p>

            <div className="project-meta">
              <span>Project #{project.id}</span>

              {project.repository_url && (
                <a
                  href={project.repository_url}
                  target="_blank"
                  rel="noreferrer"
                  onClick={(e) => e.stopPropagation()}
                >
                  <ExternalLink size={15} />
                </a>
              )}
            </div>
          </button>
        ))}
      </div>
    </>
  );
}

/* ---------------- Project Detail ---------------- */

function ProjectDetail() {
  const { projectId } = useParams();
  const navigate = useNavigate();

  const id = Number(projectId);

  const [project, setProject] = useState<Project | null>(null);
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [history, setHistory] = useState<DeploymentHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) {
      setError("Invalid project ID");
      setLoading(false);
      return;
    }

    Promise.all([
      api.project(id),
      api.environments(id),
      api.deploymentHistory(id),
    ])
      .then(([p, e, h]) => {
        setProject(p);
        setEnvironments(e);
        setHistory(h);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} />;
  if (!project) return <ErrorBox message="Project not found." />;

  return (
    <>
      <button className="back-button" onClick={() => navigate("/projects")}>
        <ArrowLeft size={16} />
        Back to Projects
      </button>

      <div className="project-header">
        <div>
          <div className="eyebrow">PROJECT #{project.id}</div>
          <h1>{project.name}</h1>

          <p className="muted">
            {project.description}
          </p>

          {project.repository_url && (
            <a
              className="repo-link"
              href={project.repository_url}
              target="_blank"
              rel="noreferrer"
            >
              <ExternalLink size={15} />
              Repository
            </a>
          )}
        </div>
      </div>

      <div className="section-heading">
        <div>
          <h2>Environments</h2>
          <p className="muted">
            Choose an environment to deploy this project.
          </p>
        </div>
      </div>

      <div className="environment-grid">
        {environments.map((environment) => (
          <EnvironmentDeployCard
            key={environment.id}
            project={project}
            environment={environment}
          />
        ))}
      </div>

      <div className="card large detail-history">
        <div className="card-header">
          <div>
            <h2>Deployment History</h2>
            <p className="muted">
              Previous pipeline executions for this project.
            </p>
          </div>
        </div>

        <HistoryTable rows={history} />
      </div>
    </>
  );
}

function EnvironmentDeployCard({
  project,
  environment,
}: {
  project: Project;
  environment: Environment;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="card environment-deploy-card">
      <div className="environment-card-top">
        <div className="environment-icon">
          <Server size={22} />
        </div>

        <StatusBadge status="ready" />
      </div>

      <h2>{environment.name}</h2>

      <p className="muted">
        Environment #{environment.id}
      </p>

      <button
        className="deploy-button"
        onClick={() => setOpen((value) => !value)}
      >
        <Rocket size={16} />
        {open ? "Close" : "Deploy"}
      </button>

      {open && (
        <DeployForm
          project={project}
          environment={environment}
        />
      )}
    </div>
  );
}

function DeployForm({
  project,
  environment,
}: {
  project: Project;
  environment: Environment;
}) {
  const [deploying, setDeploying] = useState(false);
  const [result, setResult] =
    useState<DeploymentResponse | null>(null);
  const [error, setError] = useState("");

  const [securityDetails, setSecurityDetails] =
  useState<SecurityScan | null>(null);

const [loadingSecurityDetails, setLoadingSecurityDetails] =
  useState(false);

async function handleViewSecurityDetails() {
  setLoadingSecurityDetails(true);

  try {
    const scans = await api.securityScans(project.id);

    const scan =
      scans.find(
        (item) => item.id === result?.security_scan_id,
      ) ?? scans[0];

    setSecurityDetails(scan ?? null);
  } catch {
    setSecurityDetails(null);
  } finally {
    setLoadingSecurityDetails(false);
  }
}

  async function handleDeploy(e: React.FormEvent) {
  e.preventDefault();

  setDeploying(true);
  setResult(null);
  setError("");

  try {
    const response = await api.deploy(project.id, {
      environment_id: environment.id,
    });

    setResult(response);
  } catch (err) {
    setError(
      err instanceof Error
        ? err.message
        : "Deployment failed",
    );
  } finally {
    setDeploying(false);
  }
}

  return (
    <form className="deploy-form student-deploy-form" onSubmit={handleDeploy}>
      <div className="student-deploy-header">
        <div>
          <div className="form-title">
            Deploy {project.name}
          </div>

          <p className="muted">
            NEXUS will build your project, check it for security
            issues, and deploy it automatically.
          </p>
        </div>
      </div>

      <div className="deployment-choice">
        <div className="choice-label">
          Environment
        </div>

        <div className="selected-environment">
          <div className="choice-icon">
            <Rocket size={18} />
          </div>

          <div>
            <strong>
              {environment.name.charAt(0).toUpperCase() +
                environment.name.slice(1)}
            </strong>

            <span>
              {environment.name === "development"
                ? "Recommended for testing your project"
                : "Test version before production"}
            </span>
          </div>

          <CheckCircle2 size={20} />
        </div>
      </div>

      <div className="deployment-choice">
        <div className="choice-label">
          Deployment size
        </div>

        <div className="selected-environment">
          <div className="choice-icon">
            <Boxes size={18} />
          </div>

          <div>
            <strong>Standard</strong>
            <span>
              NEXUS will choose the required infrastructure automatically.
            </span>
          </div>

          <CheckCircle2 size={20} />
        </div>
      </div>

      <div className="student-info-box">
        <ShieldCheck size={18} />

        <div>
          <strong>Protected deployment</strong>
          <span>
            NEXUS automatically builds your project and runs security
            checks before deployment. Unsafe builds are blocked.
          </span>
        </div>
      </div>

      <button
        className="deploy-button primary student-deploy-button"
        type="submit"
        disabled={deploying}
      >
        <Rocket size={17} />

        {deploying
          ? "Preparing your deployment..."
          : "Deploy Project"}
      </button>

      {error && (
        <div className="deployment-result blocked">
          <ShieldAlert size={18} />

          <div>
            <strong>Deployment Failed</strong>
            <span>{error}</span>
          </div>
        </div>
      )}

      {result && (
  <div
    className={
      result.status === "blocked"
        ? "student-deployment-result blocked"
        : "student-deployment-result success"
    }
  >
    {result.status === "blocked" ? (
      <>
        <div className="student-result-icon blocked">
          <ShieldAlert size={22} />
        </div>

        <div className="student-result-content">
          <h3>Deployment protected</h3>

          <p>
            NEXUS found security issues in your project, so the
            deployment was stopped before anything was released.
          </p>

          <div className="security-summary">
            <div>
              <strong>{result.high_count}</strong>
              <span>High severity</span>
            </div>

            <div>
              <strong>{result.critical_count}</strong>
              <span>Critical</span>
            </div>
          </div>

          <div className="student-next-steps">
            <strong>What you can do</strong>

            <ol>
              <li>Review the security issues in your project.</li>
              <li>Update affected dependencies.</li>
              <li>Run the deployment again.</li>
            </ol>
          </div>

          <button
            type="button"
            className="security-details-button"
            onClick={handleViewSecurityDetails}
            disabled={loadingSecurityDetails}
          >
            <ShieldCheck size={15} />

            {loadingSecurityDetails
              ? "Loading security details..."
              : "View Security Details"}
          </button>

          <small>
            Build #{result.build_id} · Nothing was deployed
          </small>
        </div>
      </>
    ) : (
      <>
        <div className="student-result-icon success">
          <CheckCircle2 size={22} />
        </div>

        <div className="student-result-content">
          <h3>Project deployed successfully</h3>

          <p>
            Your project passed the NEXUS checks and has been
            deployed to {environment.name}.
          </p>

          <small>
            Build #{result.build_id} · Deployment ready
          </small>
        </div>
      </>
    )}

    {/* Security details work for blocked deployments */}
    {securityDetails && (
      <div className="security-details-panel">
        <div className="security-details-header">
          <div>
            <h4>Security Check Details</h4>

            <p>
              Results from the security scan for this build.
            </p>
          </div>

          <ShieldCheck size={20} />
        </div>

        <div className="security-details-grid">
          <div>
            <strong>{securityDetails.critical_count}</strong>
            <span>Critical</span>
          </div>

          <div>
            <strong>{securityDetails.high_count}</strong>
            <span>High</span>
          </div>

          <div>
            <strong>{securityDetails.medium_count}</strong>
            <span>Medium</span>
          </div>

          <div>
            <strong>{securityDetails.low_count}</strong>
            <span>Low</span>
          </div>
        </div>

        <div className="security-details-meta">
          <span>
            Scan #{securityDetails.id}
          </span>

          <span>
            Build #{securityDetails.build_id}
          </span>

          <span>
            Status: {securityDetails.status}
          </span>
        </div>

        {securityDetails.findings.length > 0 && (
  <div className="security-findings">
    <div className="security-details-header">
      <div>
        <h4>Vulnerability Findings</h4>
        <p className="muted">
          Findings reported by Trivy for this image.
        </p>
      </div>
      <span className="security-findings-count">
        {securityDetails.findings.length} findings
      </span>
    </div>

    <div className="security-findings-table-wrap">
      <table className="security-findings-table">
        <thead>
          <tr>
            <th>Severity</th>
            <th>Package</th>
            <th>Installed</th>
            <th>Fixed Version</th>
            <th>Vulnerability</th>
          </tr>
        </thead>

        <tbody>
          {securityDetails.findings.map((finding, index) => (
            <tr
              key={`${finding.vulnerability_id}-${finding.package}-${index}`}
            >
              <td>
                <StatusBadge status={finding.severity.toLowerCase()} />
              </td>

              <td>
                <strong>
                  {finding.package ?? "Unknown package"}
                </strong>
              </td>

              <td>
                <code>
                  {finding.installed_version ?? "—"}
                </code>
              </td>

              <td>
                <code>
                  {finding.fixed_version ?? "No fix available"}
                </code>
              </td>

              <td>
                <div>
                  <strong>
                    {finding.vulnerability_id ?? "Unknown"}
                  </strong>

                  {finding.title && (
                    <div className="security-finding-title">
                      {finding.title}
                    </div>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
)}

        <div className="security-details-explanation">
          <strong>Why was deployment stopped?</strong>

          <p>
            NEXUS blocks deployments when High or Critical
            vulnerabilities are detected. Fix the affected
            dependencies and run the deployment again.
          </p>
        </div>
      </div>
    )}
  </div>
)}
    </form>
  );
}

/* ---------------- Other Pages ---------------- */

function Deployments() {
  const [history, setHistory] = useState<DeploymentHistory[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.deploymentHistory(DEFAULT_PROJECT_ID)
      .then(setHistory)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading />;

  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Deployments</h1>
          <p className="muted">
            Real deployment pipeline history from NEXUS.
          </p>
        </div>
      </div>

      <div className="card large">
        <HistoryTable rows={history} />
      </div>
    </>
  );
}

function Environments() {
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.environments(DEFAULT_PROJECT_ID)
      .then(setEnvironments)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading />;

  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Environments</h1>
          <p className="muted">
            Deployment targets for student-api.
          </p>
        </div>
      </div>

      <div className="environment-grid">
        {environments.map((environment) => (
          <div className="card environment-card" key={environment.id}>
            <div className="environment-icon">
              <Server size={22} />
            </div>

            <div>
              <h2>{environment.name}</h2>
              <p className="muted">
                Environment #{environment.id}
              </p>
            </div>

            <StatusBadge status="ready" />
          </div>
        ))}
      </div>
    </>
  );
}

function Monitoring() {
  const [deployments, setDeployments] =
    useState<KubernetesDeployment[]>([]);

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.deployments(DEFAULT_PROJECT_ID)
      .then(setDeployments)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading />;

  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Monitoring</h1>
          <p className="muted">
            Kubernetes deployment status from NEXUS.
          </p>
        </div>
      </div>

      <div className="project-grid">
        {deployments.map((deployment) => (
          <div className="card project-card" key={deployment.id}>
            <Activity size={22} />
            <h2>{deployment.application_name}</h2>

            <p className="muted">
              Image: {deployment.image_name}
            </p>

            <p className="muted">
              Namespace: {deployment.namespace}
            </p>

            <div className="project-meta">
              <span>
                {deployment.replicas} replica
              </span>

              <StatusBadge status={deployment.status} />
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

/* ---------------- Shell ---------------- */

const navigation = [
  {
    to: "/",
    label: "Dashboard",
    icon: LayoutDashboard,
    end: true,
  },
  {
    to: "/projects",
    label: "Projects",
    icon: Boxes,
  },

  {
    to: "/import",
    label: "Import GitHub",
    icon: ExternalLink,
  },
  {
    to: "/deployments",
    label: "Deployments",
    icon: Rocket,
  },
  {
    to: "/environments",
    label: "Environments",
    icon: Server,
  },
  {
    to: "/monitoring",
    label: "Monitoring",
    icon: Activity,
  },
];

function App() {
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">N</div>

          <div>
            <strong>NEXUS</strong>
            <small>Student Developer Platform</small>
          </div>
        </div>

        <nav>
          {navigation.map(
            ({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  `nav-item ${isActive ? "active" : ""}`
                }
              >
                <Icon size={18} />
                <span>{label}</span>
              </NavLink>
            ),
          )}
        </nav>

        <div className="sidebar-footer">
          <div className="mode">
            <Cloud size={16} />
            <span>Local Mode</span>
          </div>

          <div className="security">
            <ShieldCheck size={16} />
            <span>DevSecOps Enabled</span>
          </div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <span className="breadcrumb">
            NEXUS / Platform
          </span>

          <div className="status">
            <span className="status-dot" />
            API Connected
          </div>
        </header>

        <section className="content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/import" element={<ImportRepository />} />
            <Route
              path="/projects/:projectId"
              element={<ProjectDetail />}
            />
            <Route
              path="/deployments"
              element={<Deployments />}
            />
            <Route
              path="/environments"
              element={<Environments />}
            />
            <Route
              path="/monitoring"
              element={<Monitoring />}
            />
          </Routes>
        </section>
      </main>
    </div>
  );
}

export default App;
