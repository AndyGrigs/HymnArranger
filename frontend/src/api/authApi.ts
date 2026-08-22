const API_BASE = import.meta.env.VITE_API_BASE ?? '';

export interface User {
  id: string;
  email: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface WorkSummary {
  id: string;
  title: string;
  created_at: string;
  input_params: Record<string, unknown>;
}

export interface WorkDetail extends WorkSummary {
  musicxml_content: string;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers ?? {}),
    },
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // тіло не JSON — лишаємо statusText
    }
    throw new ApiError(res.status, detail);
  }

  return res.json() as Promise<T>;
}

function authHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` };
}

export function registerUser(email: string, password: string) {
  return request<User>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export function loginUser(email: string, password: string) {
  return request<{ access_token: string; token_type: string }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export function getCurrentUser(token: string) {
  return request<User>('/auth/me', { headers: authHeaders(token) });
}

export function forgotPassword(email: string) {
  return request<{ message: string }>('/auth/forgot-password', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
}

export function resetPassword(token: string, newPassword: string) {
  return request<{ message: string }>('/auth/reset-password', {
    method: 'POST',
    body: JSON.stringify({ token, new_password: newPassword }),
  });
}

export function listWorks(token: string) {
  return request<WorkSummary[]>('/works', { headers: authHeaders(token) });
}

export function getWork(token: string, workId: string) {
  return request<WorkDetail>(`/works/${workId}`, { headers: authHeaders(token) });
}

export function deleteWork(token: string, workId: string) {
  return request<{ message: string }>(`/works/${workId}`, {
    method: 'DELETE',
    headers: authHeaders(token),
  });
}