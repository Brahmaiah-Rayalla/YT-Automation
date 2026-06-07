import { useEffect, useRef, useState } from "react";
import { checkHealth, getWorkflowStatus, startWorkflow } from "../api";
import ProgressFeed from "./ProgressFeed";
import ResultsTable from "./ResultsTable";
import "./Dashboard.css";

const POLL_INTERVAL_MS = 2000;

export default function Dashboard() {
  const [youtubeHandle, setYoutubeHandle] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [executionMode, setExecutionMode] = useState("sequential");
  const [isRunning, setIsRunning] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [progress, setProgress] = useState([]);
  const [results, setResults] = useState([]);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");
  const [apiOnline, setApiOnline] = useState(null);
  const pollRef = useRef(null);

  useEffect(() => {
    checkHealth()
      .then(() => setApiOnline(true))
      .catch(() => setApiOnline(false));
  }, []);

  useEffect(() => {
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
      }
    };
  }, []);

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const pollStatus = (activeJobId) => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const data = await getWorkflowStatus(activeJobId);
        setProgress(data.progress || []);
        setResults(data.results || []);
        setStatus(data.status);

        if (data.status === "completed" || data.status === "failed") {
          setIsRunning(false);
          stopPolling();
          if (data.error) {
            setError(data.error);
          }
        }
      } catch (pollError) {
        setIsRunning(false);
        stopPolling();
        setError(pollError.message || "Failed to fetch workflow status.");
      }
    }, POLL_INTERVAL_MS);
  };

  const handleRunWorkflow = async () => {
    setError("");
    setProgress([]);
    setResults([]);
    setStatus(null);

    if (!youtubeHandle.trim()) {
      setError("YouTube handle is required (e.g. @channelname).");
      return;
    }

    setIsRunning(true);

    try {
      const response = await startWorkflow({
        youtubeHandle,
        email,
        password,
        executionMode,
      });
      setJobId(response.job_id);
      pollStatus(response.job_id);
    } catch (runError) {
      setIsRunning(false);
      const message =
        runError.response?.data?.detail ||
        runError.message ||
        "Failed to start workflow.";
      setError(typeof message === "string" ? message : JSON.stringify(message));
    }
  };

  const usingFrontendCredentials = email.trim() && password.trim();

  return (
    <div className="dashboard">
      <header className="hero">
        <div>
          <p className="eyebrow">YouTube Engagement Automation</p>
          <h1>Workflow Dashboard</h1>
          <p className="subtitle">
            Run browser automation to watch and like the most recent Short from a YouTube channel.
          </p>
        </div>
        <div className={`api-status ${apiOnline ? "online" : "offline"}`}>
          API {apiOnline === null ? "checking..." : apiOnline ? "online" : "offline"}
        </div>
      </header>

      <section className="panel controls">
        <div className="panel-header">
          <h2>Run Workflow</h2>
        </div>

        <div className="form-grid">
          <label className="full-width">
            YouTube Handle
            <input
              type="text"
              placeholder="@channelname"
              value={youtubeHandle}
              onChange={(event) => setYoutubeHandle(event.target.value)}
              disabled={isRunning}
            />
          </label>

          <label>
            Test Email
            <input
              type="email"
              placeholder="user@gmail.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              disabled={isRunning}
            />
          </label>

          <label>
            Test Password
            <input
              type="password"
              placeholder="Leave empty to use Google Drive file"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              disabled={isRunning}
            />
          </label>

          <label>
            Execution Mode
            <select
              value={executionMode}
              onChange={(event) => setExecutionMode(event.target.value)}
              disabled={isRunning}
            >
              <option value="sequential">Sequential</option>
              <option value="parallel">Parallel</option>
            </select>
          </label>
        </div>

        <p className="hint">
          Each account will open <strong>{youtubeHandle.trim() || "@channel"}</strong>, watch the latest
          Short, and like it.
          {" "}
          {usingFrontendCredentials
            ? "Credentials provided — workflow will run for this single test account."
            : "Email and password empty — workflow will load all accounts from the Google Drive credentials file."}
        </p>

        {error && <div className="alert error">{error}</div>}

        <button
          className="primary-button"
          onClick={handleRunWorkflow}
          disabled={isRunning || apiOnline === false || !youtubeHandle.trim()}
        >
          {isRunning ? "Workflow Running..." : "Run Workflow"}
        </button>

        {jobId && <p className="muted job-id">Job ID: {jobId}</p>}
      </section>

      <ProgressFeed events={progress} isRunning={isRunning} />
      <ResultsTable results={results} />

      {status === "completed" && !isRunning && (
        <div className="alert success">Workflow completed successfully.</div>
      )}
      {status === "failed" && !isRunning && (
        <div className="alert error">Workflow failed. Check the progress feed and results.</div>
      )}
    </div>
  );
}
