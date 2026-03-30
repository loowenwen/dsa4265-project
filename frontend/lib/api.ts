import { ProcessRequest, ProcessResponse, ValidationDetail } from "../types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiValidationError extends Error {
  details: ValidationDetail[];

  constructor(details: ValidationDetail[]) {
    super("Validation error");
    this.details = details;
  }
}

export async function processApplicant(payload: ProcessRequest): Promise<ProcessResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/process`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (response.status === 422) {
    const body = await response.json();
    throw new ApiValidationError(Array.isArray(body.detail) ? body.detail : []);
  }

  if (!response.ok) {
    throw new Error("Failed to process applicant data");
  }

  return response.json();
}
