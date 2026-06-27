const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(message: string, status: number, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function buildUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${BASE_URL}${normalizedPath}`;
}

async function parseError(
  response: Response,
): Promise<{ message: string; detail: unknown }> {
  try {
    const body = (await response.json()) as { detail?: unknown; message?: unknown };
    if (typeof body.detail === "string") {
      return { message: body.detail, detail: body.detail };
    }
    if (typeof body.message === "string") {
      return { message: body.message, detail: body.message };
    }
    if (body.detail !== undefined) {
      return { message: JSON.stringify(body.detail), detail: body.detail };
    }
  } catch {
    // fall through
  }
  return { message: `${response.status} ${response.statusText}`, detail: undefined };
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(buildUrl(path), {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    const { message, detail } = await parseError(response);
    throw new ApiError(message, response.status, detail);
  }
  return (await response.json()) as T;
}

export async function apiPost<T, B = unknown>(path: string, body: B): Promise<T> {
  const response = await fetch(buildUrl(path), {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const { message, detail } = await parseError(response);
    throw new ApiError(message, response.status, detail);
  }
  return (await response.json()) as T;
}

export async function apiPut<T, B = unknown>(path: string, body: B): Promise<T> {
  const response = await fetch(buildUrl(path), {
    method: "PUT",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const { message, detail } = await parseError(response);
    throw new ApiError(message, response.status, detail);
  }
  return (await response.json()) as T;
}

export async function apiDelete<T = void>(path: string): Promise<T> {
  const response = await fetch(buildUrl(path), {
    method: "DELETE",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    const { message, detail } = await parseError(response);
    throw new ApiError(message, response.status, detail);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
