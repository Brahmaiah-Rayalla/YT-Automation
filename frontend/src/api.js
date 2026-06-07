import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export async function fetchChannelShorts(youtubeHandle, limit = 10) {
  const response = await client.post("/api/shorts/list", {
    youtube_handle: youtubeHandle.trim(),
    limit,
  });
  return response.data;
}

export async function startWorkflow({
  youtubeHandle,
  shortUrl,
  accountMode,
  email,
  password,
  accounts,
  executionMode,
}) {
  const payload = {
    youtube_handle: youtubeHandle.trim(),
    short_url: shortUrl,
    account_mode: accountMode,
    execution_mode: executionMode || undefined,
  };

  if (accountMode === "single") {
    payload.email = email.trim();
    payload.password = password.trim();
  } else {
    payload.accounts = accounts;
  }

  const response = await client.post("/api/workflow/run", payload);
  return response.data;
}

export async function getWorkflowStatus(jobId) {
  const response = await client.get(`/api/workflow/status/${jobId}`);
  return response.data;
}

export async function checkHealth() {
  const response = await client.get("/api/health");
  return response.data;
}

export function parseAccountsList(text) {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const commaIndex = line.indexOf(",");
      if (commaIndex === -1) {
        return null;
      }
      return {
        email: line.slice(0, commaIndex).trim(),
        password: line.slice(commaIndex + 1).trim(),
      };
    })
    .filter((account) => account?.email && account?.password);
}
