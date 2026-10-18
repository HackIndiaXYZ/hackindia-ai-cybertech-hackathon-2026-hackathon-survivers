export const BACKEND_URL =
  (process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000").replace(/\/+$/, "");

export const AI_API_URL =
  (process.env.NEXT_PUBLIC_AI_API_URL || "http://localhost:8001").replace(/\/+$/, "");

export type ApiComplaint = {
  id: number;
  ticket_id: string;
  category: "pothole" | "garbage" | "streetlight" | "water_leakage" | "drainage";
  description: string;
  latitude: number;
  longitude: number;
  department: string | null;
  status: "submitted" | "under_review" | "assigned" | "in_progress" | "resolved" | "rejected";
  created_at: string;
};

export type DashboardComplaint = {
  id: string;
  title: string;
  category: string;
  location: string;
  priority: string;
  status: string;
  department: string;
  latitude: number;
  longitude: number;
  description: string;
  createdAt: string;
};

const categoryLabels: Record<string, string> = {
  pothole: "Pothole",
  garbage: "Garbage",
  streetlight: "Streetlight",
  water_leakage: "Water leakage",
  drainage: "Drainage",
};

const statusLabels: Record<string, string> = {
  submitted: "Submitted",
  under_review: "Under review",
  assigned: "Assigned",
  in_progress: "In progress",
  resolved: "Resolved",
  rejected: "Rejected",
};

export function toDashboardComplaint(item: ApiComplaint): DashboardComplaint {
  return {
    id: item.ticket_id,
    title: item.description.split(/\r?\n/)[0].slice(0, 160) || "Civic issue report",
    category: categoryLabels[item.category] || item.category,
    location: `${item.latitude.toFixed(5)}, ${item.longitude.toFixed(5)}`,
    priority: "Medium",
    status: statusLabels[item.status] || item.status,
    department: item.department || "Awaiting assignment",
    latitude: item.latitude,
    longitude: item.longitude,
    description: item.description,
    createdAt: item.created_at,
  };
}

async function readError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    const detail = body?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => item.msg || "Invalid request").join("; ");
    }
  } catch {
    // Use the generic status message if the response isn't JSON.
  }
  return `Request failed (${response.status} ${response.statusText})`;
}

export async function getComplaints(): Promise<DashboardComplaint[]> {
  const response = await fetch(`${BACKEND_URL}/api/complaints?limit=100`, {
    cache: "no-store",
  });
  if (!response.ok) throw new Error(await readError(response));
  const data: ApiComplaint[] = await response.json();
  return data.map(toDashboardComplaint);
}

export async function createComplaint(payload: {
  category: string;
  description: string;
  latitude: number;
  longitude: number;
}): Promise<DashboardComplaint> {
  const response = await fetch(`${BACKEND_URL}/api/complaints`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await readError(response));
  const data: ApiComplaint = await response.json();
  return toDashboardComplaint(data);
}

export async function analyzeComplaintWithAgents(complaint: string) {
  const response = await fetch(`${AI_API_URL}/complaints/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ complaint }),
  });
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}

export async function analyzeIssueImage(file: File) {
  const body = new FormData();
  body.append("file", file);

  const response = await fetch(`${BACKEND_URL}/api/analyze-image`, {
    method: "POST",
    body,
  });
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}
