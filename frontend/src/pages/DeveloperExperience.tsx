import { useEffect, useState } from "react";
import {
  CheckCircle2,
  CircleAlert,
  Clock3,
  GitBranch,
  GitCommit,
  History,
  Loader2,
  Package,
  RefreshCw,

  Server,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { useParams } from "react-router-dom";
import {
  api,
  type DeploymentHistory,
  type DeploymentStatus,
} from "../services/api";

function StatusIcon({ status }: { status: string }) {
  if (
    [
       "success",
       "passed",
       "valid",
       "published",
       "running",
       "healthy",
       "synced",
       "succeeded",
    ].includes(
      status.toLowerCase(),
    )
  ) {
    return <CheckCircle2 size={18} />;
  }

  if (["failed", "blocked", "error"].includes(status.toLowerCase())) {
    return <XCircle size={18} />;
  }

  return <CircleAlert size={18} />;
}

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

export default function DeveloperExperience() {
  const { projectId } = useParams();
  const id = Number(projectId);

  const [history, setHistory] = useState<DeploymentHistory[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);

  const [data, setData] = useState<DeploymentStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadHistory = async () => {
  if (!id) return;

  setHistoryLoading(true);

  try {
    const pipelineHistory = await api.deploymentHistory(id);

    setHistory(pipelineHistory);
  } catch (err) {
    setError(
      err instanceof Error ? err.message : "Unable to load deployment history",
    );
  } finally {
    setHistoryLoading(false);
  }
};

  const loadStatus = async () => {
    if (!id) {
      setError("Invalid project ID");
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError("");
      const result = await api.deploymentStatus(id);
      setData(result);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load deployment status",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
  void loadStatus();
  void loadHistory();
}, [id]);

  if (loading) {
    return (
      <main className="page-shell">
        <div className="loading-state">
          <Loader2 size={22} className="spin" />
          Loading deployment pipeline...
        </div>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="page-shell">
        <div className="error-state">
          <XCircle size={22} />
          <div>
            <strong>Unable to load deployment status</strong>
            <p>{error || "No deployment data found."}</p>
          </div>
          <button onClick={() => void loadStatus()}>
            <RefreshCw size={16} />
            Retry
          </button>
        </div>
      </main>
    );
  }

  const deploymentHealthy =
  data.argo.status === "available" &&
  data.argo.sync_status === "Synced" &&
  data.argo.health_status === "Healthy" &&
  data.kubernetes.ready_replicas === data.kubernetes.desired_replicas &&
  data.kubernetes.available_replicas === data.kubernetes.desired_replicas;

  const stages = [
  {
    title: "Build",
    value: `Build #${data.pipeline.build_id}`,
    status: data.pipeline.build_status,
    icon: Package,
  },
  {
    title: "Security",
    value:
      data.pipeline.security_scan_id !== null
        ? `Scan #${data.pipeline.security_scan_id}`
        : "No scan",
    status: data.pipeline.security_status,
    icon: ShieldCheck,
  },
  {
    title: "GitOps",
    value: data.gitops.revision
      ? data.gitops.revision.slice(0, 10)
      : "No revision",
    status: data.gitops.status,
    icon: GitBranch,
  },
  {
    title: "Argo CD",
    value: data.argo.revision
      ? data.argo.revision.slice(0, 10)
      : "No revision",
    status:
      data.argo.sync_status === "Synced"
        ? data.argo.health_status
        : data.argo.sync_status,
    icon: GitCommit,
  },
  {
    title: "Kubernetes",
    value: `${data.kubernetes.ready_replicas}/${data.kubernetes.desired_replicas} ready`,
    status: data.kubernetes.status,
    icon: Server,
  },
];

  return (
    <main className="page-shell">
      <section className="dx-header">
        <div>
          <div className="eyebrow">NEXUS / DEVELOPER EXPERIENCE</div>
          <h1>{data.application_name}</h1>
          <p>
            Deployment pipeline from build to GitOps reconciliation and
            Kubernetes runtime.
          </p>
        </div>

        <button
  className="refresh-button"
  onClick={() => {
    void loadStatus();
    void loadHistory();
  }}
>
  <RefreshCw size={16} />
  Refresh
</button>
      </section>

      <section className="dx-meta-grid">
        <div className="dx-meta-card">
          <span>Environment</span>
          <strong>{data.environment_name}</strong>
        </div>

        <div className="dx-meta-card">
          <span>Image</span>
          <strong>{data.image_name}</strong>
        </div>

        <div className="dx-meta-card">
          <span>Namespace</span>
          <strong>{data.kubernetes.namespace}</strong>
        </div>

        <div className="dx-meta-card">
          <span>Pipeline</span>
          <strong>#{data.pipeline.id}</strong>
        </div>
      </section>

      <section className="dx-card">
        <div className="section-heading">
          <div>
            <span className="eyebrow">DELIVERY PIPELINE</span>
            <h2>Build → Security → GitOps → Argo CD → Kubernetes</h2>
          </div>

          <span className="status-pill">
  <StatusIcon status={deploymentHealthy ? "running" : data.pipeline.status} />
  {deploymentHealthy ? "healthy" : data.pipeline.status}
</span>
        </div>

        <div className="pipeline-track">
          {stages.map((stage, index) => {
            const Icon = stage.icon;

            return (
              <div className="pipeline-stage" key={stage.title}>
                <div className="stage-icon">
                  <Icon size={20} />
                </div>

                <div className="stage-content">
                  <span>{stage.title}</span>
                  <strong>{stage.value}</strong>
                  <small>
                    <StatusIcon status={stage.status} />
                    {stage.status}
                  </small>
                </div>

                {index < stages.length - 1 && (
                  <div className="pipeline-connector" />
                )}
              </div>
            );
          })}
        </div>
      </section>

      <section className="dx-two-column dx-three-column">
        <div className="dx-card">
          <div className="section-heading">
            <div>
              <span className="eyebrow">GITOPS</span>
              <h2>Deployment revision</h2>
            </div>
            <GitCommit size={20} />
          </div>

          <div className="revision-box">
            <span>Git commit</span>
            <code>
              {data.gitops.revision || "No GitOps revision recorded"}
            </code>
          </div>

          <div className="detail-row">
            <span>Status</span>
            <strong>{data.gitops.status}</strong>
          </div>
        </div>


        <div className="dx-card">
  <div className="section-heading">
    <div>
      <span className="eyebrow">ARGO CD</span>
      <h2>Reconciliation</h2>
    </div>
    <GitCommit size={20} />
  </div>

  <div className="detail-row">
    <span>Application</span>
    <strong>{data.argo.application_name}</strong>
  </div>

  <div className="detail-row">
    <span>Sync</span>
    <strong>{data.argo.sync_status}</strong>
  </div>

  <div className="detail-row">
    <span>Health</span>
    <strong>{data.argo.health_status}</strong>
  </div>

  <div className="detail-row">
    <span>Operation</span>
    <strong>{data.argo.operation_phase || "—"}</strong>
  </div>
</div>

        <div className="dx-card">
          <div className="section-heading">
            <div>
              <span className="eyebrow">KUBERNETES</span>
              <h2>Runtime health</h2>
            </div>
            <Server size={20} />
          </div>

          <div className="replica-summary">
            <strong>
              {data.kubernetes.ready_replicas}/
              {data.kubernetes.desired_replicas}
            </strong>
            <span>ready replicas</span>
          </div>

          <div className="detail-row">
            <span>Available</span>
            <strong>{data.kubernetes.available_replicas}</strong>
          </div>

          <div className="detail-row">
            <span>Deployment</span>
            <strong>{data.kubernetes.deployment_name}</strong>
          </div>
        </div>
      </section>

      <section className="dx-card">
        <div className="section-heading">
          <div>
            <span className="eyebrow">PIPELINE DETAILS</span>
            <h2>Security & validation</h2>
          </div>
          <ShieldCheck size={20} />
        </div>

        <div className="detail-grid">
          <div className="detail-row">
            <span>Build</span>
            <strong>{data.pipeline.build_status}</strong>
          </div>

          <div className="detail-row">
            <span>Validation</span>
            <strong>{data.pipeline.validation_status}</strong>
          </div>

          <div className="detail-row">
            <span>Security</span>
            <strong>{data.pipeline.security_status}</strong>
          </div>

          <div className="detail-row">
            <span>High vulnerabilities</span>
            <strong>{data.pipeline.high_count}</strong>
          </div>

          <div className="detail-row">
            <span>Critical vulnerabilities</span>
            <strong>{data.pipeline.critical_count}</strong>
          </div>

          <div className="detail-row">
            <span>Created</span>
            <strong>{formatDate(data.pipeline.created_at)}</strong>
          </div>
        </div>
      </section>

      <section className="dx-message">
        <span className="eyebrow">PIPELINE MESSAGE</span>
        <p>{data.pipeline.message}</p>
      </section>

      <section className="dx-card dx-history">
  <div className="section-heading">
    <div>
      <span className="eyebrow">RELEASE MANAGEMENT</span>
      <h2>Deployment history</h2>
    </div>
    <History size={20} />
  </div>

  {historyLoading ? (
    <div className="loading-state">
      <Loader2 size={18} className="spin" />
      Loading history...
    </div>
  ) : history.length === 0 ? (
    <p className="history-empty">No pipeline history found.</p>
  ) : (
    <div className="history-list">
      {history.map((run) => {
        const isCurrent = run.id === data.pipeline.id;

        return (
          <article className="history-row" key={run.id}>
            <div className="history-icon">
              <Package size={18} />
            </div>

            <div className="history-main">
              <div className="history-title">
                <strong>Pipeline #{run.id}</strong>
                {isCurrent && <span className="current-badge">CURRENT</span>}
                {run.status === "gitops_pending" && isCurrent && (
                  <span className="history-state">
                    GitOps pending verification
                  </span>
                )}
                {run.status !== "gitops_pending" && (
                  <span className="history-state">{run.status}</span>
                )}
              </div>

              <p>
                Build #{run.build_id} · {run.image_name}
              </p>

              <div className="history-meta">
                <span>
                  <Clock3 size={13} />
                  {formatDate(run.created_at)}
                </span>
                <span>Security: {run.security_status}</span>
                <span>
                  High {run.high_count} · Critical {run.critical_count}
                </span>
              </div>
            </div>

          </article>
        );
      })}
    </div>
  )}
</section>
    </main>
  );
}
