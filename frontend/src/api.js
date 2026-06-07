import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export async function startWorkflow({ youtubeHandle, email, password, executionMode }) {
  const payload = {
    youtube_handle: youtubeHandle.trim(),
    execution_mode: executionMode || undefined,
  };

  if (email?.trim() && password?.trim()) {
    payload.email = email.trim();
    payload.password = password.trim();
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
