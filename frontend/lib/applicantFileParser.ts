import { ProcessRequest } from "../types/api";
import { EMPTY_FORM_VALUES, REQUIRED_FIELDS } from "./applicantForm";

const KEY_ALIASES: Record<string, keyof ProcessRequest> = {
  personage: "person_age",
  age: "person_age",
  personincome: "person_income",
  annualincome: "person_income",
  income: "person_income",
  personhomeownership: "person_home_ownership",
  homeownership: "person_home_ownership",
  personemplength: "person_emp_length",
  employmentlength: "person_emp_length",
  loanintent: "loan_intent",
  loangrade: "loan_grade",
  loanamnt: "loan_amnt",
  loanamount: "loan_amnt",
  loanintrate: "loan_int_rate",
  interestrate: "loan_int_rate",
  loanpercentincome: "loan_percent_income",
  cbpersondefaultonfile: "cb_person_default_on_file",
  defaultonfile: "cb_person_default_on_file",
  cbpersoncredhistlength: "cb_person_cred_hist_length",
  credithistorylength: "cb_person_cred_hist_length",
};

export class FileParseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "FileParseError";
  }
}

function normalizeHeader(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]/g, "");
}

function parseCsvLine(line: string): string[] {
  const values: string[] = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i += 1) {
    const char = line[i];

    if (char === '"') {
      const next = line[i + 1];
      if (inQuotes && next === '"') {
        current += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (char === "," && !inQuotes) {
      values.push(current.trim());
      current = "";
      continue;
    }

    current += char;
  }

  values.push(current.trim());
  return values;
}

function firstRecordFromCsv(text: string): Record<string, unknown> {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);

  if (lines.length < 2) {
    throw new FileParseError("CSV must include a header row and at least one data row.");
  }

  const headers = parseCsvLine(lines[0]);
  const values = parseCsvLine(lines[1]);
  const output: Record<string, unknown> = {};

  for (let i = 0; i < headers.length; i += 1) {
    output[headers[i]] = values[i] ?? "";
  }

  return output;
}

function firstRecordFromJson(text: string): Record<string, unknown> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new FileParseError("Invalid JSON file.");
  }

  if (Array.isArray(parsed)) {
    if (parsed.length === 0 || typeof parsed[0] !== "object" || parsed[0] === null) {
      throw new FileParseError("JSON array must contain at least one object row.");
    }
    return parsed[0] as Record<string, unknown>;
  }

  if (typeof parsed === "object" && parsed !== null) {
    return parsed as Record<string, unknown>;
  }

  throw new FileParseError("JSON must be an object or an array of objects.");
}

async function firstRecordFromXlsx(file: File): Promise<Record<string, unknown>> {
  const XLSX = await import("xlsx");
  const bytes = await file.arrayBuffer();
  const workbook = XLSX.read(bytes, { type: "array" });
  const firstSheet = workbook.SheetNames[0];

  if (!firstSheet) {
    throw new FileParseError("XLSX has no worksheet.");
  }

  const sheet = workbook.Sheets[firstSheet];
  const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(sheet, {
    defval: "",
    raw: false,
  });

  if (rows.length === 0) {
    throw new FileParseError("XLSX must contain at least one data row.");
  }

  return rows[0];
}

function mapRecordToForm(record: Record<string, unknown>): ProcessRequest {
  const mapped: ProcessRequest = { ...EMPTY_FORM_VALUES };

  for (const [rawKey, rawValue] of Object.entries(record)) {
    const alias = KEY_ALIASES[normalizeHeader(rawKey)] as keyof ProcessRequest | undefined;
    if (!alias) {
      continue;
    }

    mapped[alias] = String(rawValue ?? "").trim();
  }

  const missing = REQUIRED_FIELDS.filter((field) => !mapped[field].trim());
  if (missing.length > 0) {
    throw new FileParseError(`Uploaded file is missing required fields: ${missing.join(", ")}`);
  }

  return mapped;
}

export async function parseApplicantFile(file: File): Promise<ProcessRequest> {
  const extension = file.name.toLowerCase().split(".").pop();

  let record: Record<string, unknown>;
  if (extension === "json") {
    record = firstRecordFromJson(await file.text());
  } else if (extension === "csv") {
    record = firstRecordFromCsv(await file.text());
  } else if (extension === "xlsx") {
    record = await firstRecordFromXlsx(file);
  } else {
    throw new FileParseError("Unsupported file type. Please upload CSV, XLSX, or JSON.");
  }

  return mapRecordToForm(record);
}
