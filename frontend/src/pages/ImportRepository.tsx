import { useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  ExternalLink,
  FileCode2,
  
  Loader2,
  Package,
  ShieldCheck,
  TestTube2,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import { api } from "../services/api";
import type {
  BuildPlan,
  Project,
  RepositoryAnalysis,
} from "../services/api";

export default function ImportRepository() {
  const navigate = useNavigate();

  const [repositoryUrl, setRepositoryUrl] = useState("");
  const [project, setProject] = useState<Project | null>(null);
  const [analysis, setAnalysis] =
    useState<RepositoryAnalysis | null>(null);
  const [buildPlan, setBuildPlan] = useState<BuildPlan | null>(null);

  const [step, setStep] = useState<
    "idle" | "importing" | "analyzing" | "planning"
  >("idle");

  const [error, setError] = useState("");

  async function handleImport(e: React.FormEvent) {
    e.preventDefault();

    setError("");
    setProject(null);
    setAnalysis(null);
    setBuildPlan(null);

    try {
      setStep("importing");

      const imported = await api.importGithub(repositoryUrl);
      setProject(imported);

      setStep("analyzing");

      const repositoryAnalysis =
        await api.analyzeRepository(repositoryUrl);

      setAnalysis(repositoryAnalysis);

      setStep("planning");

      const plan = await api.buildPlan(imported.id);
      setBuildPlan(plan);

      setStep("idle");
    } catch (err) {
      setStep("idle");
      setError(
        err instanceof Error
          ? err.message
          : "Unable to import repository",
      );
    }
  }

  const working = step !== "idle";

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">NEXUS ONBOARDING</div>
          <h1>Import Repository</h1>
          <p className="muted">
            Bring a GitHub project into the NEXUS platform.
          </p>
        </div>
      </div>

      <div className="import-layout">
        <div className="card import-card">
          <div className="import-icon">
            <ExternalLink size={25} />
          </div>

          <h2>GitHub Repository</h2>

          <p className="muted">
            NEXUS will import the repository, analyze its
            technology stack, and generate a deployment build plan.
          </p>

          <form onSubmit={handleImport}>
            <label className="import-label">
              Repository URL

              <input
                className="import-input"
                type="url"
                placeholder="https://github.com/username/project"
                value={repositoryUrl}
                onChange={(e) =>
                  setRepositoryUrl(e.target.value)
                }
                required
                disabled={working}
              />
            </label>

            <button
              className="deploy-button primary"
              type="submit"
              disabled={working}
            >
              {working ? (
                <>
                  <Loader2 className="spin" size={17} />
                  {step === "importing"
                    ? "Importing..."
                    : step === "analyzing"
                      ? "Analyzing..."
                      : "Generating Build Plan..."}
                </>
              ) : (
                <>
                  <ExternalLink size={17} />
                  Import Repository
                </>
              )}
            </button>
          </form>

          {error && (
            <div className="form-error">
              {error}
            </div>
          )}
        </div>

        <div className="card import-flow">
          <h2>What NEXUS does</h2>

          <ImportStep
            number="01"
            title="Import"
            description="Register the GitHub repository as a NEXUS project."
            active={!!project}
          />

          <ImportStep
            number="02"
            title="Analyze"
            description="Detect languages, frameworks, Docker, CI, Kubernetes and tests."
            active={!!analysis}
          />

          <ImportStep
            number="03"
            title="Build Plan"
            description="Generate the deployment steps and container image plan."
            active={!!buildPlan}
          />

          <ImportStep
            number="04"
            title="Deploy"
            description="Choose an environment and run the DevSecOps pipeline."
            active={false}
          />
        </div>
      </div>

      {analysis && (
        <div className="card large import-section">
          <div className="card-header">
            <div>
              <h2>Repository Analysis</h2>
              <p className="muted">
                Detected capabilities from the repository.
              </p>
            </div>

            <CheckCircle2 className="success-icon" />
          </div>

          <div className="analysis-grid">
            <AnalysisItem
              label="Languages"
              value={analysis.languages.join(", ") || "None detected"}
              icon={<FileCode2 size={18} />}
            />

            <AnalysisItem
              label="Frameworks"
              value={analysis.frameworks.join(", ") || "None detected"}
              icon={<Package size={18} />}
            />

            <AnalysisItem
              label="Dockerfile"
              value={analysis.has_dockerfile ? "Detected" : "Required"}
              icon={<Package size={18} />}
              good={analysis.has_dockerfile}
            />

            <AnalysisItem
              label="CI"
              value={analysis.has_ci ? "Detected" : "Not detected"}
              icon={<ShieldCheck size={18} />}
              good={analysis.has_ci}
            />

            <AnalysisItem
              label="Kubernetes"
              value={
                analysis.has_kubernetes
                  ? "Detected"
                  : "Not detected"
              }
              icon={<Package size={18} />}
              good={analysis.has_kubernetes}
            />

            <AnalysisItem
              label="Helm"
              value={analysis.has_helm ? "Detected" : "Not detected"}
              icon={<Package size={18} />}
              good={analysis.has_helm}
            />

            <AnalysisItem
              label="Tests"
              value={analysis.has_tests ? "Detected" : "Not detected"}
              icon={<TestTube2 size={18} />}
              good={analysis.has_tests}
            />

            <AnalysisItem
              label="README"
              value={analysis.has_readme ? "Detected" : "Not detected"}
              icon={<FileCode2 size={18} />}
              good={analysis.has_readme}
            />
          </div>
        </div>
      )}

      {buildPlan && project && (
        <div className="card large import-section">
          <div className="card-header">
            <div>
              <h2>Build Plan</h2>
              <p className="muted">
                NEXUS deployment plan for {buildPlan.project_name}.
              </p>
            </div>
          </div>

          <div className="build-plan-summary">
            <div>
              <span>Build Type</span>
              <strong>{buildPlan.build_type}</strong>
            </div>

            <div>
              <span>Image</span>
              <strong>{buildPlan.image_name}</strong>
            </div>

            <div>
              <span>Target</span>
              <strong>{buildPlan.target_environment}</strong>
            </div>
          </div>

          <div className="plan-steps">
            {buildPlan.steps.map((item, index) => (
              <div className="plan-step" key={item}>
                <span>{index + 1}</span>
                <p>{item}</p>
              </div>
            ))}
          </div>

          <button
            className="deploy-button primary continue-button"
            onClick={() => navigate(`/projects/${project.id}`)}
          >
            Continue to Deployment
            <ArrowRight size={17} />
          </button>
        </div>
      )}
    </>
  );
}

function ImportStep({
  number,
  title,
  description,
  active,
}: {
  number: string;
  title: string;
  description: string;
  active: boolean;
}) {
  return (
    <div className={`import-step ${active ? "complete" : ""}`}>
      <div className="step-number">
        {active ? <CheckCircle2 size={17} /> : number}
      </div>

      <div>
        <strong>{title}</strong>
        <span>{description}</span>
      </div>
    </div>
  );
}

function AnalysisItem({
  label,
  value,
  icon,
  good = false,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  good?: boolean;
}) {
  return (
    <div className="analysis-item">
      <div className="analysis-icon">{icon}</div>

      <div>
        <span>{label}</span>
        <strong className={good ? "success-text" : ""}>
          {value}
        </strong>
      </div>
    </div>
  );
}
