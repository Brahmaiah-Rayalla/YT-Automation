import { useEffect, useRef, useState } from "react";
import {
  checkHealth,
  fetchChannelShorts,
  getWorkflowStatus,
  parseAccountsList,
  startWorkflow,
} from "../api";
import ProgressFeed from "./ProgressFeed";
import ResultsTable from "./ResultsTable";
import ShortsPicker from "./ShortsPicker";
import "./Dashboard.css";

const POLL_INTERVAL_MS = 1500;

export default function Dashboard() {
  const [youtubeHandle, setYoutubeHandle] = useState("");
  const [accountMode, setAccountMode] = useState("single");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [accountsText, setAccountsText] = useState("");
  const [executionMode, setExecutionMode] = useState("sequential");
  const [shorts, setShorts] = useState([]);
  const [selectedShort, setSelectedShort] = useState(null);
  const [isLoadingShorts, setIsLoadingShorts] = useState(false);
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

  const parsedAccounts = parseAccountsList(accountsText);
  const hasSingleCredentials = email.trim() && password.trim();
  const hasMultiCredentials = parsedAccounts.length > 0;
  const accountsReady = accountMode === "single" ? hasSingleCredentials : hasMultiCredentials;
  const canRunWorkflow =
    apiOnline !== false &&
    youtubeHandle.trim() &&
    selectedShort &&
    accountsReady &&
    !isRunning;

  const handleLoadShorts = async () => {
    setError("");
    setShorts([]);
    setSelectedShort(null);

    if (!youtubeHandle.trim()) {
      setError("YouTube handle is required before loading Shorts.");
      return;
    }

    setIsLoadingShorts(true);
    try {
      const data = await fetchChannelShorts(youtubeHandle, 10);
      setShorts(data.shorts || []);
      if (!data.shorts?.length) {
        setError("No Shorts were found for this channel.");
      }
    } catch (loadError) {
      let message =
        loadError.response?.data?.detail ||
        loadError.message ||
        "Failed to load Shorts.";
      if (loadError.response?.status === 404) {
        message =
          "Shorts API not found. Restart the backend server so it picks up the latest code, then try again.";
      }
      setError(typeof message === "string" ? message : JSON.stringify(message));
    } finally {
      setIsLoadingShorts(false);
    }
  };

  const handleRunWorkflow = async () => {
    setError("");
    setProgress([]);
    setResults([]);
    setStatus(null);

    if (!youtubeHandle.trim()) {
      setError("YouTube handle is required.");
      return;
    }
    if (!selectedShort?.url) {
      setError("Select a Short before running the workflow.");
      return;
    }
    if (!accountsReady) {
      setError(
        accountMode === "single"
          ? "Email and password are required for single account mode."
          : "Add at least one account in email,password format for multi account mode.",
      );
      return;
    }

    setIsRunning(true);

    try {
      const response = await startWorkflow({
        youtubeHandle,
        shortUrl: selectedShort.url,
        accountMode,
        email,
        password,
        accounts: parsedAccounts,
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

  return (
    <div className="dashboard">
      <header className="hero">
        <div>
          <p className="eyebrow">YouTube Engagement Automation</p>
          <h1>Workflow Dashboard</h1>
          <p className="subtitle">
            Load recent Shorts from a channel, choose one to target, then run the workflow for one
            or many accounts.
          </p>
        </div>
        <div className={`api-status ${apiOnline ? "online" : "offline"}`}>
          API {apiOnline === null ? "checking..." : apiOnline ? "online" : "offline"}
        </div>
      </header>

      <section className="panel controls">
        <div className="panel-header">
          <h2>Setup</h2>
        </div>

        <div className="form-grid">
          <label className="full-width">
            YouTube Handle
            <input
              type="text"
              placeholder="@channelname"
              value={youtubeHandle}
              onChange={(event) => {
                setYoutubeHandle(event.target.value);
                setShorts([]);
                setSelectedShort(null);
              }}
              disabled={isRunning || isLoadingShorts}
            />
          </label>

          <label>
            Account Mode
            <select
              value={accountMode}
              onChange={(event) => setAccountMode(event.target.value)}
              disabled={isRunning}
            >
              <option value="single">Single Account</option>
              <option value="multi">Multiple Accounts</option>
            </select>
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

          {accountMode === "single" ? (
            <>
              <label>
                Email
                <input
                  type="email"
                  placeholder="user@gmail.com"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  disabled={isRunning}
                  autoComplete="username"
                />
              </label>

              <label>
                Password
                <input
                  type="password"
                  placeholder="Account password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  disabled={isRunning}
                  autoComplete="current-password"
                />
              </label>
            </>
          ) : (
            <label className="full-width">
              Accounts List
              <textarea
                rows={5}
                placeholder={"user1@gmail.com,password1\nuser2@gmail.com,password2"}
                value={accountsText}
                onChange={(event) => setAccountsText(event.target.value)}
                disabled={isRunning}
              />
            </label>
          )}
        </div>

        {accountMode === "multi" && (
          <p className="hint">
            One account per line using <code>email,password</code>. Parsed accounts:{" "}
            {parsedAccounts.length}
          </p>
        )}

        <div className="action-row">
          <button
            type="button"
            className="accent-button"
            onClick={handleLoadShorts}
            disabled={isRunning || isLoadingShorts || apiOnline === false || !youtubeHandle.trim()}
          >
            {isLoadingShorts ? "Loading Shorts..." : "Load Recent Shorts"}
          </button>
        </div>

        {error && <div className="alert error">{error}</div>}
        {jobId && <p className="muted job-id">Job ID: {jobId}</p>}
      </section>

      <ShortsPicker
        shorts={shorts}
        selectedShortUrl={selectedShort?.url}
        onSelect={setSelectedShort}
        isLoading={isLoadingShorts}
        handle={youtubeHandle.trim() || "@channel"}
      />

      <ProgressFeed
        events={progress}
        isRunning={isRunning}
        onRunWorkflow={handleRunWorkflow}
        canRunWorkflow={canRunWorkflow}
        selectedShort={selectedShort}
      />
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
