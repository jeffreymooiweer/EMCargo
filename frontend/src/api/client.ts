import type { CargoManifest } from "./cargo";
import i18n from "i18next";

const API_BASE = "/api";

/** Fired on `window` when the server refuses a call because the account
 *  owes the installation a second factor (`auth.two_factor_required`).
 *  The nudge listens and takes the person to the panel that sets one up:
 *  the API client has no router of its own, and every page would
 *  otherwise have to recognise the refusal separately. */
export const TWO_FACTOR_REQUIRED_EVENT = "emcargo:two-factor-required";

/** The error for a refused response, after noticing what kind it is. */
async function refusal(res: Response): Promise<Error> {
  const err = await res.json().catch(() => ({ detail: res.statusText }));
  if (res.status === 403 && isApiMessage(err.detail) && err.detail.code === "auth.two_factor_required") {
    window.dispatchEvent(new CustomEvent(TWO_FACTOR_REQUIRED_EVENT));
  }
  return Object.assign(new Error(describeDetail(err.detail)), {
    code: isApiMessage(err.detail) ? err.detail.code : undefined,
  });
}

async function downloadBlob(path: string, filename: string): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, { credentials: "include" });
  if (!res.ok) {
    throw await refusal(res);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

async function uploadFile<T>(path: string, file: File, signal?: AbortSignal): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    credentials: "include",
    body: form,
    signal,
  });
  if (!res.ok) {
    // The import routes answer with a translatable message, so this cannot
    // assume a string any more — that assumption is what produced "Upload
    // failed" where the server had said exactly what was wrong.
    throw await refusal(res);
  }
  return res.json();
}

/** FastAPI reads a repeated parameter as a list: ?profiles=ADR&profiles=IMDG. */
function profileQuery(profiles: string[]): string {
  return profiles.map((p) => `&profiles=${encodeURIComponent(p)}`).join("");
}

/** A message the backend sends with a code, so the interface can translate it.
 *
 * The server does not translate. It cannot: an error is raised deep in a
 * service that has no idea who is asking, and the language belongs to the
 * screen. So it sends a code, the parameters that go in the sentence, and an
 * English text to fall back on. */
export interface ApiMessage {
  code: string;
  message: string;
  params?: Record<string, unknown>;
}

/** The translation for a message code, or the server's English fallback.
 *
 * The fallback is what makes this safe to deploy: a backend newer than the
 * frontend in front of it can send a code these language files do not know yet,
 * and the user still reads a sentence instead of a dotted key. */
export function translateMessage(message: ApiMessage): string {
  const fallback = message.message || message.code;
  const key = `errors.${message.code}`;
  // `t` can return the key itself, or nothing at all when i18next has not
  // finished initialising — on the very first paint, or in a unit test that
  // never loads a bundle. Neither is a translation, and neither is worth
  // showing when the server already sent a readable sentence.
  const translated = i18n.t(key, { ...(message.params ?? {}), defaultValue: fallback });
  return typeof translated === "string" && translated && translated !== key ? translated : fallback;
}

function isApiMessage(value: unknown): value is ApiMessage {
  return !!value && typeof value === "object" && typeof (value as ApiMessage).code === "string";
}

/** Make a FastAPI error readable, and in the user's language where possible.
 *
 * Three shapes arrive here, and all three used to end up as "[object Object]"
 * or as a Dutch sentence:
 *
 * - `{code, message}` — an error this application raised on purpose;
 * - a list of `{type, loc, msg, ctx}` — FastAPI's own 422, where `type` carries
 *   our code for the validators that set one;
 * - a plain string — FastAPI's built-ins, which stay English.
 *
 * The field path is kept ("products → 1 → adr_total_quantity: …") with the head
 * ("body") removed, because it adds nothing.
 */
export function describeDetail(detail: unknown): string {
  if (typeof detail === "string" && detail) return detail;
  if (isApiMessage(detail)) return translateMessage(detail);
  if (Array.isArray(detail)) {
    const lines = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (!item || typeof item !== "object") return "";
        const entry = item as { loc?: unknown[]; msg?: string; type?: string; ctx?: Record<string, unknown> };
        const where = (entry.loc ?? [])
          .filter((part) => part !== "body")
          .map((part) => String(part))
          .join(" → ");
        const fallback = entry.msg?.replace(/^Value error,\s*/, "") ?? "";
        const message = entry.type
          ? translateMessage({ code: entry.type, message: fallback, params: entry.ctx })
          : fallback;
        return where ? `${where}: ${message}` : message;
      })
      .filter(Boolean);
    if (lines.length) return lines.join("\n");
  }
  return translateMessage({ code: "request_failed", message: "Request failed" });
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  if (!res.ok) {
    throw await refusal(res);
  }
  if (res.headers.get("content-type")?.includes("application/json")) {
    return res.json();
  }
  return res as unknown as T;
}

const request = apiRequest;

export interface DocumentTemplate {
  id: string; name: string; kind: "form" | "model"; filename: string;
  pages: number; sha256: string; available: boolean;
}

export const api = {
  documentTemplates: () => request<DocumentTemplate[]>("/settings/document-templates"),
  importDocumentTemplate: async (key: string, file: File, source: string, basis: string) => {
    const body = new FormData(); body.append("file", file); body.append("source", source); body.append("rights_basis", basis);
    const response = await fetch(`${API_BASE}/settings/document-templates/${encodeURIComponent(key)}`, { method: "POST", credentials: "include", body });
    if (!response.ok) throw await refusal(response);
    return response.json() as Promise<{ ok: boolean; sha256: string }>;
  },
  readPackingDocument: (file: File, language: string, signal?: AbortSignal) =>
    uploadFile<PackingSource>(`/assistant/documents/read?language=${encodeURIComponent(language)}`, file, signal),
  proposePackingDocument: (lines: { id: string; text: string }[], signal?: AbortSignal) =>
    request<PackingProposal>("/assistant/documents/propose", { method: "POST", body: JSON.stringify({ lines }), signal }),
  work: (params: { day: string; bucket: WorkBucket; q?: string; mine?: boolean; page?: number }) =>
    request<WorkPage>(`/work?${new URLSearchParams(Object.entries(params).map(([key, value]) => [key, String(value)]))}`),
  workPeople: (shipmentId: number) => request<{ id: number; name: string }[]>(`/work/people?shipment_id=${shipmentId}`),
  changeWork: (shipmentId: number, payload: { version: number; owner_id?: number; completed?: boolean }) =>
    request<{ ok: boolean; version: number }>(`/work/shipments/${shipmentId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  myProfile: () => request<PersonalProfile>("/users/me/profile"),
  saveMyProfile: (payload: PersonalProfile) => request<User>("/users/me/profile", { method: "PUT", body: JSON.stringify(payload) }),
  changePassword: (currentPassword: string, newPassword: string) => request<{ ok: boolean; reauthenticate: boolean }>("/auth/change-password", {
    method: "POST", body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  }),
  organisationSettings: () => request<OrganisationSettings>("/settings/organisation"),
  saveOrganisationSettings: (payload: OrganisationSettings) => request<OrganisationSettings>("/settings/organisation", { method: "PUT", body: JSON.stringify(payload) }),
  dgReviews: (status = "", page = 1) => request<{ items: DgReview[]; total: number; page: number }>(`/dg-reviews?status=${encodeURIComponent(status)}&page=${page}`),
  dgReview: (id: string) => request<DgReview & { shipment: ShipmentIn }>(`/dg-reviews/${encodeURIComponent(id)}`),
  dgReviewStatus: (payload: ShipmentIn) => request<DgReview | null>("/dg-reviews/status", { method: "POST", body: JSON.stringify(payload) }),
  submitDgReview: (payload: ShipmentIn) => request<DgReview>("/dg-reviews", { method: "POST", body: JSON.stringify(payload) }),
  decideDgReview: (id: string, status: "approved" | "changes_requested", comment: string) => request<DgReview>(`/dg-reviews/${encodeURIComponent(id)}/decision`, { method: "POST", body: JSON.stringify({ status, comment }) }),
  forgetDgReview: (id: string) => request<{ ok: boolean }>(`/dg-reviews/${encodeURIComponent(id)}`, { method: "DELETE" }),
  /** Signing in is one step or two. With a second factor the answer carries
   *  a challenge instead of a session; the code goes to `loginTwoFactor`. */
  login: (username: string, password: string) =>
    request<LoginAnswer>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  loginTwoFactor: (challenge: string, code: string) =>
    request<{ user: User }>("/auth/login/two-factor", {
      method: "POST",
      body: JSON.stringify({ challenge, code }),
    }),
  twoFactorStatus: () => request<TwoFactorStatus>("/auth/two-factor"),
  twoFactorStart: (method: "totp" | "email") =>
    request<TwoFactorSetup>("/auth/two-factor/start", {
      method: "POST",
      body: JSON.stringify({ method }),
    }),
  twoFactorConfirm: (code: string) =>
    request<{ ok: boolean; recovery_codes: string[] }>("/auth/two-factor/confirm", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),
  twoFactorNewRecoveryCodes: (code: string) =>
    request<{ recovery_codes: string[] }>("/auth/two-factor/recovery-codes", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),
  twoFactorDisable: (code: string) =>
    request<{ ok: boolean }>("/auth/two-factor", {
      method: "DELETE",
      body: JSON.stringify({ code }),
    }),
  clearTwoFactorFor: (id: number) =>
    request<{ ok: boolean }>(`/users/${id}/two-factor`, { method: "DELETE" }),
  logout: () => request("/auth/logout", { method: "POST" }),
  me: () =>
    request<{
      user: User;
      admin_ready: boolean;
      two_factor_active: boolean;
      two_factor_required: boolean;
    }>("/auth/me"),
  /** Installation status; the legacy mode field is always organisation. */
  health: () =>
    request<{ status: string; app: string; version: string; mode?: "organisation" }>("/health"),
  setupStatus: () => request<{ has_admin: boolean; mode?: "organisation" }>("/setup-status"),
  parse: (payload: Record<string, unknown>) =>
    request<CalcResult>("/parse", { method: "POST", body: JSON.stringify(payload) }),
  calculate: (payload: Record<string, unknown>) =>
    request<CalcResult>("/calculate", { method: "POST", body: JSON.stringify(payload) }),
  dgInstructions: () => request<DgInstructions>("/dg/instructions"),
  assistantStep: (payload: {
    message: string;
    state: AssistantState;
    pending: AssistantPending | null;
    language: string;
    action?: "answer" | "revise" | "optional" | "add_goods";
  }) =>
    request<AssistantStepResult>("/assistant/step", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  unitCatalogue: () => request<UnitCatalogue>("/units"),
  convertUnit: (payload: {
    quantity?: number | null;
    unit?: string | null;
    density_kg_m3?: number | null;
    category?: string | null;
    mass_per_item_kg?: number | null;
    volume_per_item_m3?: number | null;
  }) => request<UnitConversion>("/units/convert", { method: "POST", body: JSON.stringify(payload) }),
  // Language and profiles travel along because the proper shipping name depends
  // on them: ADR 5.4.1.4.1 permits a German name, IMDG 5.4.1.4.1 and IATA DGR
  // 8.1.2.1 do not. The suggestion the user clicks is the text that ends up on
  // the document.
  dgLookup: (un: string, language = "nl", profiles: string[] = []) =>
    request<DgLookupResult>(
      `/dg/lookup?un=${encodeURIComponent(un)}&language=${language}${profileQuery(profiles)}`,
    ),
  dgSearch: (q: string, limit = 12, language = "nl", profiles: string[] = []) =>
    request<{ results: DgUnEntry[] }>(
      `/dg/search?q=${encodeURIComponent(q)}&limit=${limit}&language=${language}` +
        profileQuery(profiles),
    ),
  dgPackagings: (q = "", limit = 150) =>
    request<{ results: DgPackaging[] }>(`/dg/packagings?q=${encodeURIComponent(q)}&limit=${limit}`),
  mySettings: () => request<UserPreferences>("/settings/me"),
  saveMySettings: (payload: UserPreferences) =>
    request<UserPreferences>("/settings/me", { method: "PUT", body: JSON.stringify(payload) }),
  publicSettings: () => request<PublicSettings>("/settings/public"),
  changelog: (since: string) =>
    request<ChangelogResponse>(`/changelog?since=${encodeURIComponent(since)}`),
  updateStatus: () => request<UpdateStatus>("/update-status"),
  /** A fresh look at the release feed, bypassing the six-hour cache. */
  updateCheckNow: () => request<UpdateStatus>("/update-check", { method: "POST" }),
  updateCapability: () => request<UpdateCapability>("/update-capability"),
  updateState: () => request<UpdateStateAnswer>("/update-state", { cache: "no-store" }),
  updateApply: () => request<{ started: boolean; to: string }>(
    "/update-apply", { method: "POST" }),
  // Reads carrier-assigned references (AWB, booking, ENS MRN, AES ITN) out of
  // a pasted booking confirmation. Reading only; the caller decides what to
  // fill, and fills only fields that are still empty.
  parseCarrierConfirmation: (text: string) =>
    request<{ found: Record<string, string> }>("/documents/carrier-confirmation", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  // The NHM goods nomenclature for box 24 of the CIM: by code prefix or by a
  // word of the English or French label; and the words behind one code.
  nhmSearch: (q: string, limit = 10) =>
    request<{ results: NhmEntry[]; count: number }>(`/nhm?q=${encodeURIComponent(q)}&limit=${limit}`),
  nhmLookup: (code: string) => request<NhmEntry>(`/nhm/${encodeURIComponent(code)}`),
  // Whether the ENS reference and the AES ITN apply on the route in the
  // values: read off the route fields, answered per field with the ground.
  customsRoute: (values: Record<string, string>) =>
    request<{ verdicts: Record<string, CustomsVerdict> }>("/documents/customs-route", {
      method: "POST",
      body: JSON.stringify({ values }),
    }),
  settingsOptions: () => request<SettingsOptions>("/settings/options"),
  assistantStatus: () => request<AssistantStatus>("/assistant/status"),
  assistantModel: (action: "download" | "remove" | "stop") =>
    request<Record<string, unknown>>("/assistant/model", {
      method: "POST",
      body: JSON.stringify({ action }),
    }),
  instanceSettings: () => request<InstanceSettings>("/settings/instance"),
  // The UN card store: admin-only management of the imported card set. The
  // remote check runs only when asked — nothing phones home on its own.
  unCardStoreStatus: (remote = false) =>
    request<UnCardStoreStatus>(`/un-cards/status${remote ? "?remote=true" : ""}`),
  unCardStoreDownloadLatest: () =>
    request<{ ok: boolean; tag?: string; imported: number }>(
      "/un-cards/download-latest", { method: "POST" }),
  unCardStoreImport: (file: File) =>
    uploadFile<{ ok: boolean; imported: number }>("/un-cards/import", file),
  unCardStoreRemove: () =>
    request<{ ok: boolean; removed: boolean }>("/un-cards/remove", { method: "POST" }),
  saveInstanceSettings: (payload: InstanceSettings) =>
    request<InstanceSettings>("/settings/instance", { method: "PUT", body: JSON.stringify(payload) }),
  historyCounts: () => request<{ shipments: number; trips: number; deliveries: number }>("/settings/instance/history"),
  discardHistory: () =>
    request<{ ok: boolean; shipments: number; trips: number; deliveries: number }>("/settings/instance/history/discard", {
      method: "POST",
    }),
  /** Kept groupage trips. These addresses exist only beside the shipment
   *  history; the check itself (`dgTrip`) exists everywhere. */
  trips: (query: TripQuery = {}) => request<TripPage>(`/trips${auditSuffix(query)}`),
  trip: (id: number) => request<TripDetail>(`/trips/${id}`),
  keepTrip: (payload: TripIn) =>
    request<TripDetail>("/trips", { method: "POST", body: JSON.stringify(payload) }),
  updateTrip: (id: number, payload: TripIn) =>
    request<TripDetail>(`/trips/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  forgetTrip: (id: number) => request<{ ok: boolean }>(`/trips/${id}`, { method: "DELETE" }),
  /** The audit log: who did what, metadata only. Administrators only, and
   *  requires an administrator account. */
  audit: (query: AuditQuery = {}) => request<AuditPage>(`/audit${auditSuffix(query)}`),
  auditActions: () => request<{ actions: string[]; actors: string[] }>("/audit/actions"),
  auditExportUrl: (query: AuditQuery = {}) => `${API_BASE}/audit/export.csv${auditSuffix(query)}`,
  /** The shipment history. These addresses exist only on an installation
   *  that keeps its shipments (`publicSettings.history_enabled`). */
  shipments: (query: ShipmentQuery = {}) => {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== "" && value !== null) params.set(key, String(value));
    }
    const suffix = params.toString();
    return request<ShipmentPage>(`/shipments${suffix ? `?${suffix}` : ""}`);
  },
  shipment: (id: number) => request<ShipmentDetail>(`/shipments/${id}`),
  /** Departments exist only beside the history; everybody may read the
   *  list, only an administrator changes it. */
  departments: () => request<Department[]>("/departments"),
  createDepartment: (name: string) =>
    request<Department>("/departments", { method: "POST", body: JSON.stringify({ name }) }),
  renameDepartment: (id: number, name: string) =>
    request<{ id: number; name: string }>(`/departments/${id}`, { method: "PUT", body: JSON.stringify({ name }) }),
  deleteDepartment: (id: number) =>
    request<{ ok: boolean; users: number; shipments: number }>(`/departments/${id}`, { method: "DELETE" }),
  /** The safety adviser's annual report (ADR 1.8.3.3) over the kept
   *  shipments of one year — figures for the page, a workbook to keep. */
  reportYears: () => request<{ years: number[] }>("/shipments/report/years"),
  dgsaReport: (year: number, department = "", language = "nl") =>
    request<DgsaReport>(
      `/shipments/report?year=${year}&department=${encodeURIComponent(department)}&language=${encodeURIComponent(language)}`),
  downloadDgsaReport: (year: number, department = "", language = "nl") =>
    downloadBlob(
      `/shipments/report.xlsx?year=${year}&department=${encodeURIComponent(department)}&language=${encodeURIComponent(language)}`,
      `emcargo-dgsa-report-${year}.xlsx`),
  /** The report in the DVSA's shape: the form's definition, what the
   *  history can pre-fill, and the answers kept for this year and scope. */
  dgsaReportForm: (year: number, department = "", language = "nl") =>
    request<DgsaFormResponse>(
      `/shipments/report/form?year=${year}&department=${encodeURIComponent(department)}&language=${encodeURIComponent(language)}`),
  saveDgsaAnswers: (year: number, department: string, answers: DgsaAnswers) =>
    request<{ ok: boolean; saved_at: string; answers: DgsaAnswers }>(
      `/shipments/report/answers?year=${year}&department=${encodeURIComponent(department)}`,
      { method: "PUT", body: JSON.stringify({ answers }) }),
  downloadDgsaReportPdf: (year: number, department = "", language = "nl") =>
    downloadBlob(
      `/shipments/report.pdf?year=${year}&department=${encodeURIComponent(department)}&language=${encodeURIComponent(language)}`,
      `emcargo-dgsa-report-${year}.pdf`),
  /** The articles library: the organisation's own codes for what it ships,
   *  kept beside the history like the address book. */
  articles: (q = "") => request<Article[]>(`/articles${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  saveArticle: (payload: ArticleIn) =>
    request<Article>("/articles", { method: "POST", body: JSON.stringify(payload) }),
  updateArticle: (id: number, payload: ArticleIn) =>
    request<Article>(`/articles/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteArticle: (id: number) => request<{ ok: boolean }>(`/articles/${id}`, { method: "DELETE" }),
  downloadArticleTemplate: () => downloadBlob("/articles/import-template", "articles_import_template.xlsx"),
  exportArticles: () => downloadBlob("/articles/export", "articles_export.xlsx"),
  importArticlesFile: (file: File) => uploadFile<ArticleImportResult>("/articles/import", file),
  /** The address book: parties for the details step, shared by everybody,
   *  kept only beside the history. Saving a name that exists brings that
   *  one entry up to date rather than adding a second. */
  addresses: (q = "") =>
    request<Address[]>(`/addresses${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  saveAddress: (payload: AddressIn) =>
    request<Address>("/addresses", { method: "POST", body: JSON.stringify(payload) }),
  updateAddress: (id: number, payload: AddressIn) =>
    request<Address>(`/addresses/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteAddress: (id: number) =>
    request<{ ok: boolean }>(`/addresses/${id}`, { method: "DELETE" }),
  keepShipment: (payload: ShipmentIn) =>
    request<ShipmentSummary>("/shipments", { method: "POST", body: JSON.stringify(payload) }),
  updateShipment: (id: number, payload: ShipmentIn) =>
    request<ShipmentSummary>(`/shipments/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  forgetShipment: (id: number) => request<{ ok: boolean }>(`/shipments/${id}`, { method: "DELETE" }),
  /** The running entry. A draft is kept so a reload does not lose it; it is
   *  not on the shipments page and only its own author can read it. */
  runningDraft: () => request<ShipmentDetail | null>("/shipments/draft"),
  saveDraft: (payload: ShipmentIn) =>
    request<ShipmentSummary>("/shipments/draft", { method: "PUT", body: JSON.stringify(payload) }),
  discardDraft: () => request<{ ok: boolean }>("/shipments/draft", { method: "DELETE" }),
  shipmentExportUrl: (id: number) => `${API_BASE}/shipments/${id}/export.json`,
  /** The documents again: the kept bundle re-rendered by the same code as
   *  the export step's download, handed to the browser as a file. */
  shipmentDocuments: async (id: number) => {
    const res = await fetch(`${API_BASE}/shipments/${id}/documents`, {
      method: "POST",
      credentials: "include",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(describeDetail(err.detail));
    }
    const blob = await res.blob();
    const disposition = res.headers.get("content-disposition") || "";
    const match = disposition.match(/filename="?([^";]+)"?/i);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = match ? match[1] : `emcargo-documents-${id}.zip`;
    a.click();
    URL.revokeObjectURL(url);
  },
  /** Readable without a sign-in: the sign-in page shows it. */
  branding: () => request<Branding>("/branding"),
  uploadBrandLogo: (file: File) => uploadFile<Branding>("/branding/logo", file),
  removeBrandLogo: () => request<Branding>("/branding/logo", { method: "DELETE" }),
  uploadBrandModality: (key: string, file: File) =>
    uploadFile<Branding>(`/branding/modality/${key}`, file),
  removeBrandModality: (key: string) =>
    request<Branding>(`/branding/modality/${key}`, { method: "DELETE" }),
  /** Ask for a reset link. The answer is the same whether or not the
   *  account exists — deliberately, see the endpoint. */
  forgotPassword: (identifier: string) =>
    request<{ ok: boolean }>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ identifier }),
    }),
  /** Whether a reset link can still be used, asked before the form is
   *  drawn — a spent link should look spent, not fresh. */
  resetLinkValid: (token: string) =>
    request<{ valid: boolean }>(
      `/auth/reset-password/check?token=${encodeURIComponent(token)}`),
  /** Sets the password and signs the person in, unless they owe a second
   *  factor — then the answer is a challenge, exactly as at sign-in. */
  resetPassword: (token: string, newPassword: string) =>
    request<LoginAnswer>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, new_password: newPassword }),
    }),
  twoFactorSendCode: () =>
    request<{ ok: boolean }>("/auth/two-factor/send-code", { method: "POST" }),
  sendTestMail: (to: string) =>
    request<{ ok: boolean; to: string }>("/settings/instance/mail-test", {
      method: "POST",
      body: JSON.stringify({ to }),
    }),
  listUsers: () => request<User[]>("/users"),
  uploadMyAvatar: (file: File) => uploadFile<User>("/users/me/avatar", file),
  deleteMyAvatar: () => request<User>("/users/me/avatar", { method: "DELETE" }),
  /** Make an account. With `send_welcome` the new colleague gets a link to
   *  choose their own password, and `password` may be left out entirely;
   *  `welcome_mail` in the answer says what became of that invitation. */
  createUser: (payload: Record<string, unknown>) =>
    request<User & { welcome_mail: string }>("/users", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateUser: (id: number, payload: Record<string, unknown>) =>
    request<User>(`/users/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteUser: (id: number) => request<{ ok: boolean }>(`/users/${id}`, { method: "DELETE" }),
  listEquipment: () => request<EquipmentItem[]>("/equipment"),
  containerTemplates: () => request<ContainerTemplate[]>("/equipment/container-templates"),
  getEquipment: (id: number) => request<EquipmentItem & { files: EquipmentFile[] }>(`/equipment/${id}`),
  equipmentEvents: (id: number, before?: number) => request<{ events: EquipmentEvent[]; next_before: number | null }>(`/equipment/${id}/events${before ? `?before=${before}` : ""}`),
  moveEquipment: (id: number, payload: { version: number; to_location: string; availability: string; reference: string; notes: string }) =>
    request<EquipmentItem>(`/equipment/${id}/movements`, { method: "POST", body: JSON.stringify(payload) }),
  uploadEquipmentFile: (id: number, file: File) => uploadFile<EquipmentFile>(`/equipment/${id}/files`, file),
  deleteEquipmentFile: (id: number, fileId: string) => request<{ ok: boolean }>(`/equipment/${id}/files/${fileId}`, { method: "DELETE" }),
  createEquipment: (payload: Partial<EquipmentItem>) =>
    request<EquipmentItem>("/equipment", { method: "POST", body: JSON.stringify(payload) }),
  updateEquipment: (id: number, payload: Partial<EquipmentItem>) =>
    request<EquipmentItem>(`/equipment/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteEquipment: (id: number) => request<{ ok: boolean }>(`/equipment/${id}`, { method: "DELETE" }),
  downloadEquipmentTemplate: () => downloadBlob("/equipment/import-template", "materieel_import_template.xlsx"),
  // The whole library in the import's own columns — the file round-trips, so
  // it doubles as backup and hand-over. Fetched only when someone clicks.
  exportEquipmentLibrary: () => downloadBlob("/equipment/export", "materieel_export.xlsx"),
  importEquipmentFile: (file: File) => uploadFile<EquipmentImportResult>("/equipment/import", file),
  downloadWizardTemplate: () => downloadBlob("/import/wizard-template", "wizard_import_template.xlsx"),
  parseWizardImportFile: (file: File) => uploadFile<WizardFileParseResult>("/import/wizard-file", file),
  remapWizardImport: (rows: string[][], mapping: ImportMapping, hasHeader: boolean) =>
    request<WizardFileParseResult>("/import/wizard-remap", {
      method: "POST",
      body: JSON.stringify({ rows, mapping, has_header: hasHeader }),
    }),
  densities: (q = "", offset = 0, limit = 30, category = "") =>
    request<DensityPage>(`/catalog/densities?q=${encodeURIComponent(q)}&offset=${offset}&limit=${limit}&category=${encodeURIComponent(category)}&language=${encodeURIComponent(i18n.language || "nl")}`),
  catalogSearch: (q: string, limit = 25, language = "nl") =>
    request<{ results: CatalogSearchHit[] }>(
      `/catalog/search?q=${encodeURIComponent(q)}&limit=${limit}&language=${language}`,
    ),
  geoLocations: (q: string, types?: GeoLocationType[], limit = 8) =>
    request<{ results: GeoLocation[] }>(
      `/geo/locations?q=${encodeURIComponent(q)}&limit=${limit}${types?.length ? `&type=${types.join(",")}` : ""}`,
    ),
  geoBusinesses: (name: string, city: string, lang = "en") =>
    request<{ results: { name: string; address: string }[]; available: boolean }>(
      `/geo/businesses?name=${encodeURIComponent(name)}&city=${encodeURIComponent(city)}&lang=${lang}`,
    ),
  geoAddress: (q: string, lang = "en", limit = 6) =>
    request<{ results: GeoAddress[]; available: boolean }>(
      `/geo/address?q=${encodeURIComponent(q)}&lang=${lang}&limit=${limit}`,
    ),
  documentsRegistry: () => request<DocumentRegistry>("/documents/registry"),
  dgPrepare: (entries: DgEntry[], lines: LineItem[], profiles: string[], language: string) =>
    request<DgPrepareResult>("/dg/prepare", {
      method: "POST",
      body: JSON.stringify({ entries, lines, profiles, language }),
    }),
  /** The outward consignment turned round: empty uncleaned, back to the filler.
   *
   *  The transformation is the server's, not this file's, because what may
   *  *not* be carried over is a regulatory judgement — every quantity the
   *  outward consignment stated is false on the way back — and that belongs
   *  where it is tested with the rest of the regulatory code. Nothing is
   *  stored: the answer is the same shape the wizard already holds. */
  /** The public card lookup a QR code opens. No sign-in, and nothing about a
   *  consignment: which UN numbers the link named, and whether this
   *  installation holds a card for each. */
  cardLookup: (un: string, modality: string) =>
    request<{ modality: string; cards: { un_number: string; available: boolean }[] }>(
      `/cards/lookup?un=${encodeURIComponent(un)}&modality=${encodeURIComponent(modality)}`,
    ),
  /** Groupage: several consignments judged as one load. Stores nothing. */
  dgTrip: (payload: {
    consignments: { name: string; entries: unknown[] }[];
    profiles: string[];
    language: string;
    unit_max_mass_tonnes: number | null;
  }) => request<TripResult>("/dg/trip", { method: "POST", body: JSON.stringify(payload) }),
  dgReturn: (values: Record<string, string>, lines: LineItem[], dangerous_goods: DgEntry[]) =>
    request<{ values: Record<string, string>; lines: LineItem[]; dangerous_goods: DgEntry[] }>(
      "/dg/return",
      { method: "POST", body: JSON.stringify({ values, lines, dangerous_goods }) },
    ),
  dgCompliance: (entries: DgEntry[], profiles: string[], language: string) =>
    request<DgComplianceResult>("/dg/compliance", {
      method: "POST",
      body: JSON.stringify({ entries, profiles, language }),
    }),
  validateDocument: (payload: DocumentExportPayload) =>
    request<DocumentValidationResult>("/documents/validate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  exportDocument: async (payload: DocumentExportPayload) => {
    const res = await fetch(`${API_BASE}/documents/export`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      const detail = err.detail;
      if (detail && typeof detail === "object" && Array.isArray(detail.errors)) {
        throw new Error(detail.errors.map(describeDetail).join("\n"));
      }
      throw new Error(typeof detail === "string" ? detail : "Export failed");
    }
    const blob = await res.blob();
    const disposition = res.headers.get("content-disposition") || "";
    const match = disposition.match(/filename="?([^";]+)"?/i);
    const contentType = res.headers.get("content-type") || "";
    const ext = contentType.includes("pdf") ? "pdf" : "xlsx";
    const filename = match ? match[1] : `${payload.document_key}_${Date.now()}.${ext}`;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  },
  /** One archive with every ready document, plus the UN cards and the
   *  instructions in writing for the journey's regimes. What the server
   *  cannot include it writes into the archive's README instead of
   *  leaving out silently. */
  /** The same archive, sent instead of downloaded. The server builds it
   *  with the same code the download uses, so the mail carries what the
   *  download would have. */
  mailBundle: (payload: {
    bundle: DocumentBundlePayload;
    to: string[];
    subject: string;
    message: string;
  }) =>
    request<{ ok: boolean; to: string[]; filename: string }>(
      "/documents/export/bundle/mail",
      { method: "POST", body: JSON.stringify(payload) },
    ),
  exportBundle: async (payload: DocumentBundlePayload) => {
    const res = await fetch(`${API_BASE}/documents/export/bundle`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      const detail = err.detail;
      if (detail && typeof detail === "object" && Array.isArray(detail.errors)) {
        throw new Error(detail.errors.map(describeDetail).join("\n"));
      }
      throw new Error(typeof detail === "string" ? detail : "Export failed");
    }
    const blob = await res.blob();
    const disposition = res.headers.get("content-disposition") || "";
    const match = disposition.match(/filename="?([^";]+)"?/i);
    const filename = match ? match[1] : `emcargo-documents-${Date.now()}.zip`;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  },
  writtenInstructions: () =>
    request<{ documents: WrittenInstruction[] }>("/documents/instructions"),
  /** Any model the regulation prints rather than describes, by provision:
   *  5.4.3 for the instructions in writing, 8.6.3 for the ADN checklist. */
  models: (provision: string) =>
    request<{ provision: string; documents: WrittenInstruction[] }>(
      `/documents/models/${provision}`,
    ),
  downloadModel: async (provision: string, regime: string, language: string) => {
    const res = await fetch(
      `${API_BASE}/documents/models/${provision}/${regime}/${language}`,
      { credentials: "include" },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(describeDetail(err.detail));
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${regime}-${provision.replace(/\./g, "-")}-${language}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
  downloadInstructions: async (regime: string, language: string) => {
    const res = await fetch(`${API_BASE}/documents/instructions/${regime}/${language}`, {
      credentials: "include",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(describeDetail(err.detail));
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${regime}-2025-instructions-${language}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  },
  unCardsAvailability: (payload: UnCardsPayload) =>
    request<UnCardsAvailability>("/documents/un-cards/availability", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  downloadUnCards: async (payload: UnCardsPayload) => {
    const res = await fetch(`${API_BASE}/documents/un-cards`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(typeof err.detail === "string" ? err.detail : "Download failed");
    }
    const blob = await res.blob();
    const disposition = res.headers.get("content-disposition") || "";
    const match = disposition.match(/filename="?([^";]+)"?/i);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = match ? match[1] : `un_cards_${Date.now()}.zip`;
    a.click();
    URL.revokeObjectURL(url);
  },
};

/** One model of the instructions in writing: a regime, a language, and
 *  whether this installation's document store can produce it. */
export interface WrittenInstruction {
  regime: string;
  language: string;
  available: boolean;
  document_id?: string;
  edition?: string;
  provision?: string;
  source?: string;
  from_document?: string;
  reason?: string;
  needs?: string;
}

/** What the administrator sees of the imported UN card set. */
export interface UnCardStoreLocal {
  installed: boolean;
  location: string;
  generated_at?: string;
  imported_at?: string | null;
  generator_version?: string;
  editions?: Record<string, string | null>;
  counts?: Record<string, number>;
  total_cards?: number;
  total_size?: number;
  unavailable_modalities?: Record<string, string>;
}

export interface UnCardStoreRemote {
  available: boolean;
  reachable?: boolean;
  tag?: string;
  published_at?: string;
  package_size?: number;
  update_available?: boolean;
  error?: string;
}

export interface UnCardStoreStatus {
  local: UnCardStoreLocal;
  remote?: UnCardStoreRemote;
}

export interface UnCardsPayload {
  dangerous_goods?: unknown[] | null;
  /** DG profiles of the journey (ADR/RID/ADN/IMDG/IATA): cards exist per
   *  UN number and regime, so the selection follows the modality. */
  profiles?: string[];
  output_language?: string;
}

export interface UnCardsAvailability {
  enabled: boolean;
  requested: string[];
  modalities: string[];
  available: string[];
  missing: string[];
  cards: { un_number: string; modality: string; file: string }[];
  count: number;
  library_size: number;
}

export interface User {
  execution_only?: boolean;
  display_name?: string;
  id: number;
  username: string;
  email: string;
  role: string;
  active: boolean;
  /** Whose kept shipments they see; null is the unassigned pool. Only
   *  meaningful on an installation that keeps its shipments. */
  department_id?: number | null;
  avatar_url?: string | null;
}

/** A group of users whose kept shipments are theirs to see. */
export interface Department {
  id: number;
  name: string;
  users: number;
  shipments: number;
}

/** One party in the address book: what the details step's consignor,
 *  consignee and carrier fields hold, kept under a name. */
export interface Address {
  id: number;
  name: string;
  address: string;
  contact: string;
}

export interface AddressIn {
  name: string;
  address?: string;
  contact?: string;
}

/** A row of the annual report that carries quantities: kilograms and litres
 *  apart, and a count of substances whose quantity had no usable unit. */
export interface DgsaQuantityRow {
  shipments: number;
  products: number;
  quantity_kg: number;
  quantity_l: number;
  quantity_unknown: number;
}

/** The safety adviser's annual report as the server counts it. The texts
 *  (basis, notes, duties) come localised, in the language asked for. */
export interface DgsaReport {
  year: number;
  language: string;
  generated_at: string;
  generated_by: string;
  scope: string;
  basis: string;
  source: string;
  counted_note: string;
  totals: DgsaQuantityRow & { with_dangerous_goods: number; without_dangerous_goods: number };
  by_month: { month: number; shipments: number; with_dangerous_goods: number }[];
  by_modality: { modality: string; label: string; shipments: number; with_dangerous_goods: number }[];
  by_regulation: { regulation: string; shipments: number }[];
  by_department: { department: string; shipments: number; with_dangerous_goods: number }[];
  by_class: ({ class: string } & DgsaQuantityRow)[];
  by_un_number: ({ un_number: string; name: string; class: string; packing_group: string } & DgsaQuantityRow)[];
  adr_points: { status: string; label: string; shipments: number }[];
  documents: { document: string; label: string; shipments: number }[];
  carriage_modes?: string[];
  high_consequence?: { un_number: string; reason: string; carriage_mode: string; shipments: number }[];
  class7_packages?: number;
  duties_heading: string;
  duties: { key: string; text: string }[];
}

/** One question of the DVSA-shaped form, localised by the server. */
export interface DgsaQuestion {
  key: string;
  section: string;
  kind: "text" | "textarea" | "date" | "yesno" | "yesnona" | "choice" | "multi" | "incidents" | "transport_table";
  text: string;
  checklist?: string;
  prefill?: string;
  options?: string[];
  option_labels?: Record<string, string>;
  columns?: Record<string, string>;
  operations?: string[];
  operation_labels?: Record<string, string>;
  bands?: string[];
  band_note?: string;
  classes?: string[];
  package_designs?: string[];
  package_design_labels?: Record<string, string>;
}

export interface DgsaSection {
  key: string;
  title: string;
  intro?: string;
  only_with_class?: string;
}

export interface DgsaYesNo {
  answer: "yes" | "no" | "na" | "";
  details: string;
}

export interface DgsaIncident {
  date: string;
  place: string;
  description: string;
}

export interface DgsaTransportRow {
  operations: string[];
  band: string;
  designs?: string[];
  other?: string;
  quantity_kg?: number;
  quantity_l?: number;
  packages?: number;
  shipments?: number;
}

export type DgsaAnswerValue = string | string[] | DgsaYesNo | DgsaIncident[] | Record<string, DgsaTransportRow>;
export type DgsaAnswers = Record<string, DgsaAnswerValue>;

export interface DgsaFormDefinition {
  source: string;
  answer_labels: Record<string, string>;
  sections: DgsaSection[];
  questions: DgsaQuestion[];
  checklist: {
    title: string;
    columns: Record<string, string>;
    additional_heading: string;
    items: { code: string; text: string; question?: string; kind?: string; additional?: boolean }[];
  };
}

export interface DgsaFormResponse {
  report: DgsaReport;
  scope: string;
  definition: DgsaFormDefinition;
  prefill: DgsaAnswers & { _labels?: Record<string, string> };
  answers: DgsaAnswers;
  saved_at: string | null;
  has_signature: boolean;
}

/** A kept shipment as the shipments page lists it: the index columns copied
 *  out of the structured export at save time. */
export interface ShipmentSummary {
  cargo_revision?: number;
  id: number;
  reference: string;
  modality: string;
  language: string;
  regulations: string[];
  consignor_name: string;
  consignee_name: string;
  goods_count: number;
  has_dangerous_goods: boolean;
  /** Whether a bundle was kept, so the documents can be handed out again. */
  has_documents: boolean;
  /** Entry still in progress rather than a kept shipment. */
  is_draft?: boolean;
  created_by: string;
  /** The keeper's department when it was kept; empty when none. */
  department_id?: number | null;
  department?: string;
  created_at: string;
  updated_at: string;
}

export interface ShipmentDetail extends ShipmentSummary {
  /** The wizard's own state, opaque to the server; see wizard/snapshot.ts. */
  snapshot: Record<string, unknown>;
  /** The structured export as it was kept (format emcargo.shipment). */
  export: Record<string, unknown>;
}

export interface ShipmentPage {
  items: ShipmentSummary[];
  total: number;
  page: number;
  per_page: number;
}

export type WorkBucket = "attention" | "waiting" | "today" | "ready" | "closed" | "all";
export interface WorkItem {
  kind: "shipment" | "review";
  id: string;
  reference: string;
  modality: string;
  consignor: string;
  consignee: string;
  status: "prepare" | "documents" | "ready" | "review_required" | "review" | "waiting" | "changes" | "approved";
  due_date: string | null;
  owner_id: number | null;
  owner_name: string;
  completed_at: string | null;
  version: number;
  issues: string[];
  updated_at: string;
  is_draft: boolean;
  overdue: boolean;
  review_status: string;
}
export interface WorkPage {
  items: WorkItem[];
  counts: Record<WorkBucket, number>;
  total: number;
  page: number;
  per_page: number;
  day: string;
  history_enabled: boolean;
}

/** What the export step hands over to be kept. The server builds the
 *  structured export from the parts itself, so the kept record is produced
 *  by the same code as the downloadable one. */
export interface ShipmentIn {
  cargo?: CargoManifest;
  expected_cargo_revision?: number | null;
  dg_review_id?: string;
  modality: string;
  language: string;
  profiles: string[];
  values: Record<string, string>;
  lines: LineItem[];
  dangerous_goods?: DgEntry[];
  documents: string[];
  bundle: DocumentBundlePayload | null;
  snapshot: Record<string, unknown>;
  /** Entry still in progress: kept so a reload does not lose it, and not a
   *  kept shipment until it is saved without this. */
  draft?: boolean;
}

export interface ShipmentQuery {
  q?: string;
  modality?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  per_page?: number;
  /** An administrator's filter: a department id, or "none" for the
   *  unassigned. Anybody else sees their own department whatever this says. */
  department?: string;
}

/** What is on the door: the installation's name and the addresses of its
 *  own pictures, `null` where the default applies. The addresses carry a
 *  version, so a changed picture is a new address and the old one may be
 *  cached for as long as the browser likes. */
export interface Branding {
  name: string;
  logo: string | null;
  modalities: Record<string, string | null>;
}

export type ThemeChoice = "light" | "dark" | "system";

/** Optional self-service details, separate from identity and permissions. */
export interface PersonalProfile {
  display_name: string;
  first_name: string;
  last_name: string;
  job_title: string;
  phone_number: string;
}

/** Preferences follow the account to another device. */
export interface UserPreferences {
  language: string;
  theme: ThemeChoice;
  default_modality: string;
  default_unit: string;
  prefill_documents: boolean;
  consignor_name: string;
  consignor_address: string;
  consignor_contact: string;
  carrier_name: string;
  loading_point: string;
  emergency_contact: string;
  signature_image: string;
  last_seen_version: string;
}

/** One release as the changelog records it. The body is markdown and stays in
 *  English — the repository's language — while the card's chrome is translated. */
export interface ChangelogEntry {
  version: string;
  date: string;
  body: string;
}

export interface ChangelogResponse {
  /** The version actually running, which is what gets stored as seen. */
  version: string;
  entries: ChangelogEntry[];
  truncated: boolean;
}

/** Whether a newer release exists. Three shapes, kept distinct: the check is
 *  off, GitHub could not say (which is not "up to date"), or a comparison. */
export interface UpdateStatus {
  enabled: boolean;
  current: string;
  reachable?: boolean;
  latest?: string;
  url?: string;
  update_available?: boolean;
}

/** Whether this installation can replace its own container, and if not,
 *  which of the operator's prerequisites is missing. */
export interface UpdateCapability {
  /** Compatibility field; installation capability is reported by available. */
  apply_enabled: boolean;
  socket: boolean;
  container: string | null;
  image: string | null;
  available: boolean;
  reason:
    | "no_socket"
    | "socket_permission"
    | "container_not_found"
    | "socket_unusable"
    | "foreign_image"
    | "native"
    | "kubernetes"
    | null;
  /** How the installation runs: the image, a native service, or a pod. The
   *  two that are not Docker have no in-app updater and name their own route. */
  install_method?: "docker" | "native" | "kubernetes";
}

export interface UpdateStateAnswer {
  state: {
    phase: "pulling" | "handed_over" | "stopping" | "done" | "failed";
    to?: string;
    to_image?: string;
    error?: string;
    at?: string;
  } | null;
  current: string;
}

/** The assistant runtime's condition: which mode it runs in, whether the
 *  model is installed, and how an install in progress is doing. */
export interface AssistantStatus {
  available: boolean;
  mode: "model" | "unavailable";
  model: string | null;
  installed: boolean;
  installable: boolean;
  architecture: string;
  download: { state: string; detail: string };
  running: boolean;
}

/** Signing in: either a session, or a challenge asking for the second step. */
export type LoginAnswer =
  | { user: User; two_factor_required?: undefined }
  | {
      two_factor_required: true;
      method: "totp" | "email";
      code_sent: boolean;
      challenge: string;
    };

export interface TwoFactorStatus {
  active: boolean;
  method: string;
  required: boolean;
  recovery_codes_left: number;
}

export interface TwoFactorSetup {
  method: string;
  secret: string;
  qr_svg: string;
  code_sent: boolean;
}

/** The assessment of the selected load; persistence is a separate operation. */
export interface TripResult {
  consignments: { name: string; points: number | null; exempt: boolean | null; status: string }[];
  adr_points: {
    total_points: number; threshold: number; status: string;
    incomplete_products?: string[]; forbidden_products?: string[];
    mode_note?: string; basis_note?: string; still_required?: string;
  };
  mixed_loading: { message: string; products?: string; rule?: string; severity?: string }[];
  lq_eq?: {
    status?: string;
    rows?: { product: string; lq?: { status: string; message: string }; eq?: { status: string; message: string } }[];
    warnings?: { message: string; products?: string; rule?: string; severity?: string }[];
  };
  lq_marking: {
    rule: string;
    message: string;
    lq_gross_kg: number;
    required: boolean | null;
    reason: string;
    orange_plates_required: boolean | null;
  };
  exemption_lost: { message: string; consignments: string[] } | null;
}

/** One line of the audit log. The summary is the application's own words —
 *  a reference, a document key, the settings keys that changed — and never a
 *  value from a form. */
export interface AuditEvent {
  id: number;
  at: string;
  actor_id: number | null;
  actor_username: string;
  action: string;
  target_type: string;
  target_id: string;
  summary: string;
  client: string;
}

export interface AuditPage {
  items: AuditEvent[];
  total: number;
  page: number;
  per_page: number;
}

export interface AuditQuery {
  actor?: string;
  /** A full code (`shipment.kept`) or a group (`shipment`). */
  action?: string;
  since?: string;
  until?: string;
  page?: number;
  per_page?: number;
}

/** A consignment as it sits on a kept trip: its name, its dangerous goods
 *  entries, and the kept shipment it was picked from when it was. */
export interface TripConsignment {
  name: string;
  entries: Record<string, unknown>[];
  shipment_id?: number | null;
  profiles?: string[] | null;
  route_label?: string;
}

/** A groupage trip as the groupage page hands it over to be kept. The
 *  server runs the check itself; what is kept is its own answer. */
export interface TripIn {
  name: string;
  consignments: TripConsignment[];
  profiles: string[];
  language: string;
  unit_max_mass_tonnes: number | null;
}

export interface TripSummary {
  id: number;
  name: string;
  language: string;
  regulations: string[];
  consignment_count: number;
  total_points: number | null;
  exemption_lost: boolean;
  unit_max_mass_tonnes: number | null;
  created_by: string;
  department_id?: number | null;
  department?: string;
  created_at: string;
  updated_at: string;
}

export interface TripDetail extends TripSummary {
  consignments: TripConsignment[];
  /** The check's answer as it was given when the trip was kept. */
  result: TripResult;
  /** The editions that answer was computed against. */
  editions: Record<string, unknown>;
}

export interface TripPage {
  items: TripSummary[];
  total: number;
  page: number;
  per_page: number;
}

export interface TripQuery {
  q?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  per_page?: number;
  department?: string;
}

function auditSuffix(query: AuditQuery | TripQuery): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== "" && value !== null) params.set(key, String(value));
  }
  const suffix = params.toString();
  return suffix ? `?${suffix}` : "";
}

/** What the whole installation is set to. Administrators only. */
export interface InstanceSettings {
  default_language: string;
  default_theme: ThemeChoice;
  address_lookup_enabled: boolean;
  address_api_url: string;
  address_timeout_seconds: number;
  catalog_auto_sync: boolean;
  update_check_enabled: boolean;
  un_cards_enabled: boolean;
  session_timeout_minutes: number;
  /** How many days the audit log keeps a line before start-up prunes it. */
  audit_retention_days: number;
  /** Whether this installation keeps its shipments. Off destroys data, so
   *  the server refuses to switch it off while kept shipments or trips
   *  exist; `historyCounts` says how many and `discardHistory` deletes them. */
  history_enabled: boolean;
  dg_review_enabled?: boolean;
  super_user_dgsa_enabled?: boolean;
  organisation_name: string;
  organisation_address: string;
  /** What the screen calls itself; empty means EMCargo. The logo and the
   *  tile pictures beside it are uploads, not settings — see `Branding`. */
  brand_name: string;
  two_factor_policy: "off" | "admins" | "everyone";
  public_url: string;
  /** Whether the QR code on a document opens a public page of UN cards.
   *  Off unless an administrator turns it on: it is the only route in the
   *  application that answers without a sign-in. */
  card_links_enabled: boolean;
  mail_enabled: boolean;
  mail_host: string;
  mail_port: number;
  mail_security: "starttls" | "ssl" | "none";
  mail_username: string;
  /** Write-only: the server never sends the stored password back, and an
   *  empty value on save means "keep the one you have". */
  mail_password: string;
  /** Whether a password is stored at all — the field itself stays empty. */
  mail_password_set: boolean;
  mail_from: string;
  mail_from_name: string;
  mail_timeout_seconds: number;
}

/** The part of the instance settings every signed-in user may read. */
export interface PublicSettings {
  default_language: string;
  default_theme: ThemeChoice;
  address_lookup_enabled: boolean;
  un_cards_enabled: boolean;
  /** Whether documents will carry a QR code to the public card page. */
  card_links_enabled: boolean;
  organisation_name: string;
  organisation_address: string;
  /** Whether a mail server exists, so the export step may offer to mail. */
  mail_enabled: boolean;
  /** Whether this installation keeps its shipments. Optional so an older
   *  mocked answer still type-checks; the server always sends it. */
  history_enabled?: boolean;
  dg_review_enabled?: boolean;
  super_user_dgsa_enabled?: boolean;
}

/** The lists the settings screen offers, from the backend that owns them. */
export interface SettingsOptions {
  languages: string[];
  modalities: string[];
  units: { code: string; symbol: string }[];
}

export interface DensityReferenceData {
  canonical_name: string;
  label: string;
  density_kg_m3: number;
  density_min_kg_m3: number | null;
  density_max_kg_m3: number | null;
  kind: "measurement_mean" | "measurement" | "manufacturer_specification" | "literature_reference" | "published_reference" | "unverified";
  basis: string | null;
  source_name: string | null;
  source_url: string | null;
  record_count: number | null;
  condition_key: string | null;
  temperature_c?: number | null;
  pressure_kpa?: number | null;
  phase?: string | null;
  method?: string | null;
  expanded_uncertainty_kg_m3?: number | null;
  original_value?: number | null;
  original_unit?: string | null;
  manufacturer?: string | null;
}

export interface DensityPage {
  total: number;
  offset: number;
  results: DensityReferenceData[];
}

export interface LineItem {
  cargo_goods_id?: number;
  equipment?: EquipmentSnapshot | null;
  equipment_role?: "cargo" | "container";
  container_line_id?: number | null;
  package_transport_volume_m3?: number | null;
  container_load?: { tare_kg: number | null; cargo_kg: number; gross_kg: number | null; complete: boolean; line_ids: number[] };
  line_id: number;
  raw: string;
  description: string;
  output_description: string;
  quantity: number | null;
  unit: string | null;
  material: string | null;
  /** Category of the recognised commodity, "liquid" or "bulk_material" for
   *  instance. Determines which units and forms the dropdowns suggest first. */
  material_category?: string | null;
  density_reference?: DensityReferenceData | null;
  /** The form computed with: solid, stacked, loose bulk. */
  cargo_form?: string | null;
  product_type: string | null;
  weight_each_kg: number | null;
  weight_total_kg: number | null;
  material_volume_m3: number | null;
  transport_volume_m3: number | null;
  length_cm: number | null;
  width_cm: number | null;
  height_cm: number | null;
  status: string;
  messages: string[];
  include: boolean;
  input_language?: string;
  dangerous_goods?: boolean;
  detected_un_numbers?: string[];
  dg_name_candidates?: DgNameCandidate[];
  /** Net content of one package as the description said it ("25 L"), when
   *  the line counts packages and the sentence named what each one holds. */
  package_content?: string | null;
  /** The article this line was picked from, carried along so the DG step
   *  can seed the product with what the library knows. */
  article?: ArticleRef | null;
}

/** An article of the organisation's own library: its code, and what the
 *  library knows about the substance and its packaging. */
export interface Article {
  id: number;
  code: string;
  name: string;
  un_number: string;
  proper_shipping_name: string;
  technical_name: string;
  class: string;
  packing_group: string;
  type_of_package: string;
  net_per_package: string;
  notes: string;
  active: boolean;
}

export type ArticleIn = Omit<Article, "id">;

/** What a goods line keeps of the article it was picked from. */
export type ArticleRef = Pick<Article, "code" | "name" | "un_number" | "proper_shipping_name" | "technical_name" | "class" | "packing_group" | "type_of_package" | "net_per_package">;

export interface ArticleImportResult {
  created: number;
  updated: number;
  skipped: number;
  errors: unknown[];
}

/** A substance recognised by name in the line's description. A suggestion for
 *  the user to confirm — the backend never classifies on it by itself. */
export interface DgNameCandidate {
  un: string;
  name: string;
  class: string;
  packing_group?: string;
}

/** The wizard state as the assistant exchanges it: the same data the wizard
 *  holds, in the shape the stateless /assistant/step endpoint takes and
 *  returns. Nothing of the conversation is stored on the server. */
export interface AssistantState {
  document_evidence?: DocumentEvidence[];
  modality?: string;
  draft_lines?: Record<string, unknown>[];
  dg_entries?: DgEntry[];
  doc_values?: Record<string, string>;
  selected_docs?: string[] | null;
  skipped_questions?: string[];
  include_optional?: boolean;
}

export interface PackingSourceLine { id: string; text: string; confidence: number | null }
export interface PackingSourcePage {
  number: number; method: "text" | "ocr"; lines: PackingSourceLine[];
  warnings: string[]; preview: string; corrected?: boolean;
}
export interface PackingSource { name: string; sha256: string; pages: PackingSourcePage[] }
export interface PackingGood {
  description: string; quantity: number | null; unit: string; weight_kg: number | null;
  weight_basis: "each" | "total" | "unknown"; dimensions: string;
  dimensions_cm?: { length_cm: number; width_cm: number; height_cm: number } | null;
  source_ids: string[]; excerpt: string;
}
export interface PackingField { key: string; value: string; source_ids: string[]; excerpt: string }
export interface PackingProposal { goods: PackingGood[]; fields: PackingField[]; warnings: string[] }
export interface DocumentEvidence {
  name: string; sha256: string; pages: number[]; excerpt: string;
  method: "text" | "ocr" | "corrected"; target: string; value: string;
}

export interface AssistantPending {
  scope: string;
  field?: string;
  required?: boolean;
  options?: string[];
  option_labels?: Record<string, unknown>;
  /** Lay phrasing of the question per language; the formal label and the
   *  help with its article references sit behind the info mark. */
  simple?: Record<string, string>;
  label?: Record<string, string> | string;
  help?: Record<string, string> | string;
  [key: string]: unknown;
}

export interface AssistantEvent {
  kind: string;
  [key: string]: unknown;
}

export interface AssistantReview {
  facts: (AssistantPending & { value: unknown; editable?: boolean })[];
  remaining_required: number;
  optional_count: number;
  documents: string[];
  has_dangerous_goods: boolean;
  deferred_count: number;
}

export interface AssistantStepResult {
  state: AssistantState;
  events: AssistantEvent[];
  pending: AssistantPending | null;
  review?: AssistantReview;
}

export interface CalcResult {
  success: boolean;
  column_map: Record<string, number | null>;
  lines: LineItem[];
  totals: Record<string, number>;
  errors: unknown[];
}

export interface DgProduct {
  un_number?: string;
  proper_shipping_name?: string;
  technical_name?: string;
  class?: string;
  subsidiary_risks?: string;
  packing_group?: string;
  packing_instruction?: string;
  flashpoint?: string;
  type_of_package?: string;
  quantity_packages?: string;
  quantity_items_per_package?: string;
  /** Net per inner packaging, with unit — for the LQ/EQ check (3.4/3.5). */
  net_per_inner_packaging?: string;
  net_mass_liters_per_package?: string;
  gross_mass_per_package?: string;
  /** Class 1 only: total net explosive mass in kg (ADR 1.1.3.6.3). */
  net_explosive_mass?: string;
  /** 5.4.1.2, what certain classes add to the transport document. Each is a
   * statement the consignor owes the carrier that no table can supply. */
  control_temperature?: string;
  emergency_temperature?: string;
  end_of_holding_time?: string;
  specific_gas_name?: string;
  responsible_person?: string;
  firework_classification?: string;
  /** The temperature the goods are offered at — it decides the elevated
   * temperature mark of IMDG 5.3.2.2 and ADR/RID/ADN 5.3.3. */
  carriage_temperature?: string;
  /** Set by /dg/prepare for substances that may not be carried. */
  transport_forbidden?: boolean;
  /** How these goods travel; absent means packages. */
  carriage_mode?: string;
  /** The code on the tank that is actually standing there, for ADR 4.3. */
  tank_code?: string;
  /** 5.4.1.1.3 / 5.4.1.1.6.1 / 5.4.1.1.5: waste, empty uncleaned, salvage. */
  is_waste?: string;
  empty_uncleaned?: string;
  salvage_packaging?: string;
  /** ADN 7.1.5.0.2: the goods travel exclusively in containers. */
  containers_only?: string;
  /** 5.4.1.1.23 / 5.4.1.1.19 / 5.4.1.1.20. */
  molten?: string;
  residue_classes?: string;
  classified_2_1_2_8?: string;
  /** 3.1.2.2: the most applicable of several proper shipping names, and its
   *  English counterpart where the document pairs them. */
  chosen_name?: string;
  chosen_name_en?: string;
  /** What ADR 4.3.2.2 needs and table A does not carry. */
  filling_temperature?: string;
  density_15?: string;
  density_50?: string;
  /** Which hold this is in, or "deck" — ADN 7.1.4.11.1. */
  hold?: string;
  /** The container it travels in, if any — ADN 7.1.4.11.2. */
  container_number?: string;
  eq_lq_points?: string;
  dimensions?: string;
  additional_information?: string;
  caliber?: string;
  marine_pollutant?: string;
  imdg_source_reference?: string;
  imdg_source_reviewed?: string;
  cargo_aircraft_only?: string;
  overpack?: string;
  emergency_contact?: string;
  ems_code?: string;
  transport_category?: string;
  adr_total_quantity?: string;
  q_net_quantity?: string;
  q_max_net_quantity?: string;
  classification_code?: string;
  tunnel_code?: string;
  labels?: string;
  hazard_number?: string;
  iata_packing_instruction?: string;
  limited_quantity?: string;
  excepted_quantity?: string;
}

export interface DgEntry {
  line_id: number;
  vehicle: string;
  registration?: string;
  products: DgProduct[];
}

export interface DgPrepareHint {
  line_id?: number;
  product_index?: number;
  un_number?: string;
  ems_source?: string;
  ems_class_default?: string;
  ems_description?: string;
  ems_variants?: { label: string; code: string; description: string }[];
  ems_packing_group_options?: Record<string, string>;
  excepted_quantity_text?: string;
  limited_quantity_text?: string;
  /** A warning when several Table A rows are still in the running for this UN
   *  number. Kept under the old name as well, because it is the key the
   *  interface, the export and the tests already read. */
  packing_group_note?: string;
  /** The relative density as ADN table C prints it, with the caveat that the
   *  consignor's own product may differ. */
  density_note?: string;
  table_a_variant_note?: string;
  air_note?: string;
  air_forbidden?: boolean;
  segregation_groups?: string[];
  segregation_groups_text?: string;
  marine_pollutant_text?: string;
  imdg_stowage_codes?: string[];
  imdg_stowage_text?: string;
  imdg_segregation_codes?: string[];
  imdg_segregation_text?: string;
  /** The description of every code from IMDG 7.1.5, 7.1.6 and 7.2.8. */
  imdg_stowage_definitions?: { code: string; text: string }[];
  imdg_segregation_definitions?: { code: string; text: string }[];
  imdg_stowage_category?: string;
  /** What IMDG Amendment 42-24 changes about this substance. */
  imdg_amendment_changes?: string[];
  imdg_document_requirement?: { section: string; text: string; fields: string[] };
  /** From the Dangerous Goods List itself, chapter 3.2 of the IMDG Code. */
  imdg_special_provisions?: string[];
  imdg_packing_instructions?: string;
  imdg_packing_provisions?: string;
  imdg_tank_instructions?: string;
  imdg_tank_provisions?: string;
  imdg_subsidiary_hazards?: string;
  imdg_properties?: string;
  /** The list marks this entry as amended by 42-24. */
  imdg_amended_in_42_24?: boolean;
  imdg_dgl_source?: string;
  imdg_amendment?: string;
  transport_forbidden?: boolean;
  transport_forbidden_note?: string;
  label_reference_note?: string;
}

/** One question the DG step still has to ask for a product: a fact of the
 *  consignment no table can supply, with the reason it is asked. */
export interface DgOpenQuestion {
  field: string;
  required: boolean;
  reason: string;
  /** Closed answer set for this question (the 3.1.2.2 name alternatives);
   *  rendered as a select. Absent for free-text questions. */
  options?: string[];
}

export interface DgOpenQuestionBlock {
  line_id: number;
  product_index: number;
  un_number?: string;
  questions: DgOpenQuestion[];
}

export interface DgPrepareResult {
  entries: DgEntry[];
  document_lines: Record<string, string[]>;
  hints: DgPrepareHint[];
  requirements: string[];
  open_questions?: DgOpenQuestionBlock[];
  adr_category_totals?: {
    statement: string;
    categories: { transport_category: string; total: string }[];
  };
}

export interface DgLookupResult {
  un_number: string;
  proper_shipping_name: string;
  class: string;
  subsidiary_risks?: string;
  classification_code?: string;
  packing_group?: string;
  packing_instruction?: string;
  transport_category?: string | number | null;
  tunnel_restriction_code?: string | null;
  limited_quantity?: string | null;
  source?: string;
}

export interface DgInstructions {
  dg_intro: { nl: string; en: string };
  dg_fields: Record<
    string,
    {
      label: LocalizedText;
      help: LocalizedText;
      /** A closed set of answers, rendered as a list. The mode of carriage is
       *  the first: free text there would fall through every check that
       *  branches on it. */
      type?: string;
      options?: { value: string; label: LocalizedText }[];
    }
  >;
}

export interface CatalogSearchHit {
  equipment?: EquipmentSnapshot;
  id: string;
  source: "equipment" | "profile" | "reference" | "template" | "material";
  label: string;
  sublabel: string | null;
  value: string;
  score: number;
}

export type GeoLocationType = "airport" | "port" | "station";

export interface GeoLocation {
  type: GeoLocationType;
  name: string;
  code: string;
  icao?: string;
  country: string;
  city?: string;
  subdivision?: string;
}

export interface GeoAddress {
  label: string;
  name: string;
  street: string;
  housenumber: string;
  postcode: string;
  city: string;
  state: string;
  country: string;
  countrycode: string;
}

export type EquipmentKind = "vehicle" | "machine" | "container" | "other";
export interface EquipmentInspection {
  id: string; kind: "general" | "csc" | "nen3140" | "fgas" | "apk" | "lifting" | "water" | "fire" | "other";
  name?: string; scope?: string; performed_on?: string | null; due_on?: string | null;
  result: "unknown" | "passed" | "failed" | "conditional" | "not_applicable";
  inspector?: string; reference?: string; notes?: string; archived?: boolean;
}
export interface ContainerTemplate {
  id: string; name: string; language_labels: Record<string, string>; family: string; size_ft: number;
  supplier: string; source_url: string; checked_on: string; basis: "supplier_example" | "cut_down_nominal" | "base_shell" | "mass_conflict";
  length_cm: number; width_cm: number; height_cm: number;
  inner_length_cm?: number | null; inner_width_cm?: number | null; inner_height_cm?: number | null;
  weight_kg?: number | null; max_payload_kg?: number | null; max_gross_kg?: number | null;
  container_use: string;
}
export interface TransportConfiguration {
  name: string; length_cm?: number | null; width_cm?: number | null; height_cm?: number | null;
  weight_kg: number; instructions?: string;
}
export interface EquipmentSnapshot {
  equipment_id: number; version: number; specifications: string; kind: EquipmentKind;
  asset_code?: string; container_number?: string; registration?: string; serial_number?: string;
  length_cm?: number | null; width_cm?: number | null; height_cm?: number | null; weight_kg: number;
  inner_length_cm?: number | null; inner_width_cm?: number | null; inner_height_cm?: number | null;
  max_payload_kg?: number | null; max_gross_kg?: number | null;
  transport_instructions?: string; accessories?: string; configuration?: string;
  configurations?: TransportConfiguration[];
}
export interface EquipmentFile { id: string; name: string; kind: string; size: number; created_at: string; }
export interface EquipmentEvent {
  id: number; action: string; actor_name: string; from_location: string; to_location: string;
  availability: string; reference: string; notes: string; created_at: string;
}
export interface EquipmentItem {
  kind?: EquipmentKind; version?: number; asset_code?: string; container_number?: string;
  brand?: string; model_name?: string; registration?: string; serial_number?: string; propulsion?: string;
  transport_instructions?: string; accessories?: string; container_type?: string;
  container_template_id?: string; container_use?: string; facilities?: string[]; inspections?: EquipmentInspection[];
  inner_length_cm?: number | null; inner_width_cm?: number | null; inner_height_cm?: number | null;
  max_payload_kg?: number | null; max_gross_kg?: number | null; inspection_due?: string | null;
  current_location?: string; availability?: string; condition?: string;
  planned_reference?: string; planned_date?: string | null;
  configurations?: TransportConfiguration[]; photo_url?: string | null; file_count?: number;
  id?: number;
  /** Millimetres, as a wall is written down. */
  wall_thickness_mm?: number | null;
  specifications: string;
  length_cm?: number | null;
  width_cm?: number | null;
  height_cm?: number | null;
  weight_kg: number;
  aliases?: string[];
  language_labels?: Record<string, string>;
  source?: string | null;
  notes?: string | null;
  active?: boolean;
}

export interface EquipmentImportResult {
  created: number;
  updated: number;
  skipped: number;
  /** One entry per unusable row, translated by the interface. */
  errors: ApiMessage[];
}

export interface ImportColumn {
  index: number;
  header: string;
  samples: string[];
}

export interface ImportMapping {
  description: number | null;
  quantity: number | null;
  unit: number | null;
}

export interface ImportAnalysis {
  columns: ImportColumn[];
  mapping: ImportMapping;
  /** "header": the heading row was recognised. "position": guessed from the order. */
  source: "header" | "position" | "user" | "none";
  has_header: boolean;
}

export interface WizardFileParseResult {
  text: string;
  has_header: boolean;
  analysis: ImportAnalysis;
  rows: string[][];
}

/** Dutch and English are always there; a third language can be missing in a
 *  registry that comes from elsewhere. Use `localised()` to get text out of it —
 *  that falls back instead of showing nothing. */
export type LocalizedText = { nl: string; en: string; de?: string; fr?: string };

export type FieldStatus =
  | "AUTO_DERIVED"
  | "USER_REQUIRED"
  | "USER_OPTIONAL"
  | "CONDITIONAL"
  | "CARRIER_PROVIDED"
  | "OPERATIONAL"
  | "SIGNATURE_REQUIRED"
  | "FIXED_TEMPLATE_TEXT";

export interface DocumentFieldOption {
  value: string;
  label: LocalizedText;
}

export interface DocumentField {
  key: string;
  label: LocalizedText;
  status: FieldStatus;
  type: "text" | "textarea" | "number" | "date" | "select" | "checkbox";
  options?: DocumentFieldOption[];
  condition?: string;
  auto_from?: string;
  help?: LocalizedText;
}

export interface DocumentSection {
  key?: string;
  ref?: string;
  label?: LocalizedText;
  fields?: DocumentField[];
}

export interface DocumentDefinition {
  key: string;
  label: LocalizedText;
  short_label: LocalizedText;
  category: string;
  issue_status: LocalizedText;
  /** "avc" fills in an official form, just as "pdf_template" does. */
  exporter: "generic" | "pdf_template" | "avc";
  output_format?: "xlsx" | "pdf";
  dg_profile: string | null;
  dg_only?: boolean;
  /** Carries data for another system — the JSON export, the EDI notification —
   *  rather than a document that travels with the goods. */
  data_exchange?: boolean;
  default_selected?: boolean;
  sections: DocumentSection[];
  signature_note?: LocalizedText;
}

export interface ModalityDefinition {
  key: string;
  label: LocalizedText;
  description: LocalizedText;
  documents: string[];
}

export interface DocumentRegistry {
  registry_version: string;
  field_statuses: Record<FieldStatus, LocalizedText>;
  modalities: ModalityDefinition[];
  shared_sections: DocumentSection[];
  documents: DocumentDefinition[];
  modality_defaults?: Record<string, string>;
  /** Which document carries the 5.4.1 particulars per modality — the one the
   *  advice may honestly call required when dangerous goods are on board. */
  dg_transport_documents?: Record<string, string>;
}

export interface DgUnEntry {
  un: string;
  name_en: string;
  name_de: string;
  /** Column (2) of Table A in the Dutch ADR edition; empty where it has none. */
  name_nl: string;
  /** The name in the language permitted for the chosen profiles. */
  proper_shipping_name: string;
  class: string;
  classification_code: string;
  packing_group: string;
  labels: string;
  special_provisions: string;
  limited_quantity: string;
  excepted_quantity: string;
  packing_instructions: string;
  transport_category: string;
  tunnel_code: string;
  hazard_number: string;
}

export interface DgPackaging {
  code: string;
  category: string;
  label: { nl: string; en: string };
  contents: string;
}

export interface DocumentExportPayload extends Record<string, unknown> {
  cargo?: CargoManifest;
  document_key: string;
  values: Record<string, string>;
  lines: LineItem[];
  dangerous_goods?: DgEntry[];
  output_language: string;
  signature_image?: string;
  /** Which regulations the consignment travels under. Only the documents that
   *  answer differently per regime read it — the package label sheet is the
   *  first, because the IMDG Code marks the proper shipping name on every
   *  package where the land regimes ask for it on Class 1 and Class 7 only.
   *  Left off, that sheet would quietly hand a sea consignment the road
   *  answer. */
  profiles?: string[];
  /** The transport mode the wizard was in. Recorded by the structured export
   *  so a reader knows which regime's documents the consignment was drawn up
   *  for; no document derives anything from it. */
  modality?: string;
}

export interface DocumentBundlePayload extends Record<string, unknown> {
  cargo?: CargoManifest;
  documents: DocumentExportPayload[];
  dangerous_goods?: DgEntry[];
  profiles?: string[];
  output_language: string;
  include_un_cards?: boolean;
  include_instructions?: boolean;
  signature_image?: string;
}

/** One six-digit NHM code with its labels (English and French, as the UIC
 *  publishes them) and the NST 2007 group it maps to. */
export interface NhmEntry {
  code: string;
  en: string;
  fr: string;
  nst: string;
}

/** One customs reference field's condition, decided by the route. `unknown`
 *  is the route the reader could not place — the interface then says
 *  nothing and the question stays with the person, as before. */
export interface CustomsVerdict {
  field: "ens_mrn" | "aes_itn";
  applies: "yes" | "no" | "exempt" | "unknown";
  /** The ground, translated by the interface under `customsRoute.<reason>`. */
  reason: string;
  origin: string | null;
  destination: string | null;
}

export interface DocumentValidationResult {
  document_key: string;
  errors: string[];
  warnings: string[];
}

export interface AdrPointsRow {
  product: string;
  transport_category: string | null;
  quantity: number | null;
  factor?: number | null;
  points: number | null;
}

export interface AdrPointsResult {
  rows: AdrPointsRow[];
  total_points: number;
  threshold: number;
  /** `not_available_for_mode` is 1.1.3.6.2: the exemption is granted for goods
   *  carried in packages, so a tank or bulk load cannot claim it whatever the
   *  quantity — and the arithmetic that tests it does not apply. */
  status:
    | "exempt_possible"
    | "above_threshold"
    | "not_exempt"
    | "incomplete"
    | "not_available_for_mode";
  mode_note?: string;
  not_in_packages?: string[];
  /** Lines with a transport prohibition are not in the count. */
  forbidden_products?: string[];
  category0_products: string[];
  incomplete_products: string[];
  quantity_units_note: string;
  exempt_provisions: string[];
  still_required: string[];
  /** Which tables were computed with, for example "ADR 1.1.3.6". */
  basis?: string;
  /** What the chosen mode says about this basis itself. For RID, that
   *  1.1.3.6.3/1.1.3.6.4 prescribe the same categories, factors and value 1000;
   *  for ADN, that it has no points at all and is assessed separately. */
  basis_note?: string | null;
}

export interface AdnExemptionRow {
  product: string;
  class?: string;
  selector?: string;
  limit: number | null;
  quantity: number | null;
}

/** ADN 1.1.3.6.1: exemption on gross mass, with a limit of its own per class.
 *  No points count — ADN does not have one. */
export interface AdnExemptionResult {
  rows: AdnExemptionRow[];
  total_gross_mass_kg: number;
  threshold: number;
  status:
    | "exempt_possible"
    | "above_threshold"
    | "not_exempt"
    | "incomplete"
    /** 1.1.3.6.1 is for carriage in packages; a tank or bulk load is not. */
    | "not_available_for_mode";
  /** Present with `not_available_for_mode`: which positions, and why. */
  mode_note?: string;
  over_class_limit: { class: string; selector: string; limit: number; carried: number }[];
  incomplete_products: string[];
  basis: string;
  conditions: string[];
  note: string;
}

/** ADN 7.1.4.3 — how far apart packages must lie in a vessel's holds.
 *
 *  Not the road rule renamed: ADR 7.5.2 asks whether two packages may share a
 *  vehicle and answers yes or no; this asks how many metres must lie between
 *  them. Two of its three provisions are stated in blue cones, and where the
 *  cone count for a substance could not be settled the substance is named in
 *  `cones_not_settled` rather than guessed at. */
export interface AdnHoldSeparationResult {
  status: "ok" | "not_checked" | "not_available_for_mode";
  scope?: "packages_in_holds";
  findings: {
    provision: string;
    metres?: number;
    message: string;
    two_cones?: string[];
    one_cone_flammable?: string[];
  }[];
  not_assessed?: string;
  cones_not_settled?: string[];
  /** Chapter 7.1 is for dry cargo vessels; a cargo tank load is not on one. */
  mode_note?: string;
  source?: string;
}

/** ADN 7.1.5.0 — the blue cones or blue lights the vessel must show.
 *
 *  `cones` of 0 is an answer and not a silence: it means the vessel shows none.
 *  Under 7.1.5.0.4 the heaviest signal on board wins, so one package can set the
 *  signals for everything else — `set_by` names which. */
export interface AdnSignalsResult {
  status: "ok" | "not_checked" | "not_available_for_mode";
  provision?: string;
  cones?: number;
  message?: string;
  set_by?: string[];
  highest_wins?: string;
  containers_note?: string;
  not_assessed?: string | null;
  cones_not_settled?: string[];
  /** Chapter 7.1 is for dry cargo vessels; a cargo tank load is not on one. */
  mode_note?: string;
  source?: string;
}

/** ADN 3.2.1, column (8) — may these goods travel this way on the water?
 *
 *  Empty means packages only, `B` adds bulk (7.1.1.11) and `T` adds tank vessels
 *  (7.2.1.21), where table C takes over — and this repository does not carry
 *  table C, which is what `not_assessed` says. A tank container is not judged by
 *  column (8) at all: 7.1.1.18 puts it under the requirements for packages. */
export interface AdnCarriageAdmissionResult {
  status: "ok" | "not_permitted" | "not_checked";
  items: {
    position: string;
    mode: "tank" | "portable_tank" | "bulk";
    permitted: boolean;
    provision?: string;
    message: string;
    /** Table C column (6): the tank vessel type, where every variant agrees. */
    vessel_type?: string;
    /** The types seen across variants, where they differ. */
    vessel_types?: string[];
    vessel_message?: string;
  }[];
  /** Table C's remaining per-row conditions are shown, not checked. */
  conditions_note?: string;
  /** Rows the Dutch export lacks rest on one reading, and say so. */
  single_reading_note?: string;
  not_assessed?: string;
  source?: string;
}

/** ADR 3.2.1 — may these goods travel in a tank at all?
 *
 *  Column (12) is absolute: no tank code, no carriage in an ADR tank. Column
 *  (10) is not: no portable tank instruction means not permitted *unless the
 *  competent authority allows it* under 6.7.1.3, which is why an item can be
 *  `permitted: false` and still carry `subject_to_approval`. */
export interface AdrTankAdmissionResult {
  status: "ok" | "not_permitted" | "not_checked";
  items: {
    position: string;
    mode: "tank" | "portable_tank";
    permitted: boolean;
    subject_to_approval?: boolean;
    provision?: string;
    tank_code?: string;
    tank_vehicle?: string;
    tank_provisions?: string;
    portable_tank_instructions?: string;
    portable_tank_provisions?: string;
    message: string;
  }[];
  source?: string;
}

/** ADR 4.3: may *this* tank carry these goods?
 *
 *  Column (12) says which code the substance requires; it does not say whether
 *  the tank standing on the yard may carry it. 4.3.3.1.2 answers that for gases
 *  with a hierarchy of codes, 4.3.4.1.2 for classes 3 to 9 with the rationalized
 *  approach, where the offered code names the group of substances it may carry.
 *
 *  `cannot_be_assessed` is an answer, not a failure: the seed's cells are
 *  settled by two readings or they are not, and the check declines rather than
 *  guessing. `fits_under_condition` carries a condition the consignor has to
 *  check — a vapour pressure limit, or a test pressure that comes from a table
 *  this application does not hold. */
export interface AdrTankFitResult {
  status: "ok" | "not_permitted" | "not_checked";
  items: {
    position: string;
    offered: string;
    required: string;
    fit?: "fits" | "fits_under_condition" | "does_not_fit" | "cannot_be_assessed";
    condition?: string;
    unsettled?: string[];
    tank_provisions?: string;
    provisions_note?: string;
    message: string;
  }[];
  source?: string;
}

/** ADR 4.3.2.2: how full the tank may be.
 *
 *  Four maxima, differing only in their numerator, all over 1 + α (50 − tF).
 *  Which one applies turns on the fourth letter of the tank code — N vents, H
 *  is hermetically closed — and on whether the substance is toxic or corrosive;
 *  the second half is a derivation and is shown as one. Table A carries neither
 *  density, so `needs_input` is the normal state until the consignor supplies
 *  them, and the formula is then the answer that goes on the document. */
export interface AdrFillingDegreeResult {
  status: "ok" | "not_checked";
  items: {
    position: string;
    status: "computed" | "needs_input" | "above_fifty" | "own_rule" | "no_tank_code";
    provision?: string;
    case?: string;
    numerator?: number;
    formula?: string;
    derivation?: string;
    alpha?: number;
    degree?: number;
    filling_temperature?: number;
    message: string;
  }[];
  source?: string;
}

export interface ComplianceWarning {
  rule: string;
  severity: "error" | "warning" | "info";
  message: string;
  products: string;
}

export type LqEqStatus =
  | "within_limits"
  | "not_within"
  | "not_permitted"
  | "incomplete"
  | "no_data";

export interface LqEqRow {
  product: string;
  position: string | number | null;
  lq: { value: string | null; status: LqEqStatus; message: string };
  eq: { code: string | null; status: LqEqStatus; message: string };
}

/** ADR/IMDG 3.4 and 3.5: the entered quantities tested against columns 7a/7b. */
export interface LqEqResult {
  rows: LqEqRow[];
  status: "checked" | "incomplete" | "not_checked";
  warnings: ComplianceWarning[];
  basis: string;
  basis_note?: string | null;
  note: string;
}

/** ADR 8.6.3: the tunnel restriction code derived for the whole load.
 *
 *  `status` says what happened, and the difference matters more than the code:
 *  `exempt` means 8.6.3.3 leaves the goods out of the determination entirely,
 *  `lq_marking_only` that the goods are exempt but the unit's 3.4.13 mark
 *  brings a category E restriction with it anyway. */
export interface AdrTunnelResult {
  rows: { product: string; code: string | null }[];
  /** Null where nothing was determined. */
  code: string | null;
  restricted_categories: string[];
  /** Total net explosive mass, only for the codes that split on it. */
  explosive_mass_kg: number | null;
  status: "derived" | "unrestricted" | "exempt" | "lq_marking_only" | "incomplete" | "unknown_code" | "not_checked";
  message: string;
  basis: string;
  note: string;
}

/** ADR 8.1.4 / 8.1.5: the equipment the transport unit has to carry, derived
 *  from the hazard label numbers of the load as 8.1.5.1 prescribes. A checklist,
 *  not a finding — EMCargo cannot see what is actually in the cab. */
export interface AdrEquipmentResult {
  items: { key: string; rule: string; text: string }[];
  /** The label numbers the list was derived from. */
  labels: string[];
  status: "derived" | "not_checked";
  basis: string;
  note: string;
}

/** ADR 5.3 — what goes on the outside of the vehicle. Carriage in packages:
 *  `placards_required` is false for everything but class 1 and class 7. */
export interface AdrPlacardingResult {
  status: "ok" | "exempt" | "not_checked";
  scope?: "packages";
  placards: { class: string | null; provision: string; message: string; products: string[] }[];
  placards_required?: boolean;
  marks: {
    kind: "orange_plates" | "numbered_plates" | "environmental_mark" | "exempt";
    provision: string;
    message: string;
    hazard_number?: string;
    un_number?: string;
    applies?: boolean;
  }[];
  source?: string;
}

/** ADN 5.3 — what the cargo transport units on board a dry cargo vessel must
 *  show. The kind of unit (container, road vehicle, wagon) is not visible to
 *  the application, so the placement rules come per kind, each under its own
 *  provision. A cargo tank consignment gets a mode note instead of an answer. */
export interface AdnPlacardingResult {
  status: "ok" | "not_available_for_mode" | "not_checked";
  scope?: "packages" | "tanks_or_bulk";
  mode_note?: string;
  placards: {
    class: string | null;
    provision: string;
    message: string;
    products: string[];
    label_models?: string[];
    required?: boolean | null;
  }[];
  placards_required?: boolean;
  marks: {
    kind: "orange_plates" | "tank_plates" | "sea_chain" | "environmental_mark" | "exempt_note";
    provision: string;
    message: string;
    required?: boolean | null;
  }[];
  source?: string;
}

/** RID 5.3 — what the wagons and large containers on the rail leg must show.
 *  Package wagons placard for every class; the orange plates attach only via
 *  column (20); the shunting labels of 5.3.4 are a named condition. */
/** IMDG 5.3 — what the cargo transport unit going on board must show.
 *
 * Its own kinds rather than the land regimes': the sea chapter marks the
 * proper shipping name on the unit and has a marine pollutant mark, and it
 * has no orange plates at all — the UN number rides in the placard or on a
 * panel beside it. */
export interface ImdgPlacardingResult {
  status: "ok" | "not_checked";
  scope?: "packages" | "tanks_or_bulk";
  placards: {
    class: string | null;
    provision: string;
    message: string;
    products: string[];
    label_models?: string[];
    required?: boolean | null;
  }[];
  placards_required?: boolean;
  marks: {
    kind:
      | "proper_shipping_name"
      | "un_number"
      | "marine_pollutant"
      | "elevated_temperature"
      | "limited_quantities"
      | "seawater"
      | "removal";
    provision: string;
    message: string;
    required?: boolean | null;
  }[];
  source?: string;
}

export interface RidPlacardingResult {
  status: "ok" | "not_checked";
  scope?: "packages" | "tanks_or_bulk";
  placards: {
    class: string | null;
    provision: string;
    message: string;
    products: string[];
    label_models?: string[];
    required?: boolean | null;
  }[];
  placards_required?: boolean;
  marks: {
    kind: "orange_plates" | "shunting_labels" | "orange_band" | "environmental_mark";
    provision: string;
    message: string;
    required?: boolean | null;
  }[];
  source?: string;
}

/** ADR 1.10.3 — high consequence dangerous goods. For carriage in packages the
 *  table has no thresholds to compare against: a line either qualifies at any
 *  quantity or is outside 1.10.3 at every quantity. */
export interface AdrSecurityResult {
  status: "high_consequence" | "ok" | "not_checked";
  scope?: "packages";
  items: {
    position: string | null;
    un_number: string | null;
    reason: string;
    threshold_kg: number | null;
    not_answered?: boolean;
  }[];
  message?: string;
  provision?: string;
  source?: string;
}

export interface QValueResult {
  position: string | number;
  components: { product: string; net_quantity: number; max_per_package: number; ratio: number }[];
  /** Null when there was nothing to compute or the input was incomplete. */
  q_value: number | null;
  exceeded: boolean | null;
  status?: "ok" | "exceeded" | "incomplete" | "not_checked";
  note: string;
}

/** Whether the Q check of 5.0.2.11 was actually performed. Belongs with the
 *  result, so the export sees it too and not only this panel. */
export interface QCheckStatus {
  status: "checked" | "incomplete" | "exceeded" | "not_checked";
  message: string;
}

export interface DgComplianceResult {
  sources: Record<string, string>;
  profiles: string[];
  adr_points?: AdrPointsResult;
  /** With the ADN profile only: its own exemption of 1.1.3.6.1. */
  adr_tank_admission?: AdrTankAdmissionResult;
  /** ADR 7.3.1.1: may the goods travel in bulk, and in what. Same shape. */
  adr_bulk_admission?: AdrTankAdmissionResult;
  adr_tank_fit?: AdrTankFitResult;
  adr_filling_degree?: AdrFillingDegreeResult;
  adn_carriage_admission?: AdnCarriageAdmissionResult;
  adn_exemption?: AdnExemptionResult;
  adn_hold_separation?: AdnHoldSeparationResult;
  adn_signals?: AdnSignalsResult;
  adr_mixed_loading?: ComplianceWarning[];
  /** The same caveat as `basis_note`, for the mixed loading of 7.5.2. */
  adr_mixed_loading_basis_note?: string;
  /** RID 5.4.1.1.1 (j): the hazard identification number on the CIM. Rail only —
   *  the ADR's own addition to the description line is the tunnel code. */
  rid_transport_document?: ComplianceWarning[];
  /** ADN 5.4.1.1.1 (j): the confirmation of stabilisation ST01 asks for. */
  adn_stabilisation?: ComplianceWarning[];
  /** Special provision 274: N.O.S. entries missing their technical name. */
  technical_name_findings?: ComplianceWarning[];
  /** Rule sets that have run out without anything taking their place. */
  rule_set_warnings?: ComplianceWarning[];
  /** What this result was computed with. */
  regulatory_manifest?: {
    manifest_id: string;
    editions: Record<string, string>;
    expired: string[];
  };
  imdg_segregation?: ComplianceWarning[];
  imdg_source_findings?: ComplianceWarning[];
  imdg_note?: string;
  imdg_segregation_groups?: {
    note: string;
    class8_exception: string;
    groups: { code: string; label: string }[];
  };
  iata_segregation?: ComplianceWarning[];
  /** LQ/EQ check of 3.4/3.5 — present with the ADR, RID, ADN and IMDG profiles. */
  lq_eq?: LqEqResult;
  /** Tunnel restriction code for the whole load — road only. */
  adr_tunnel?: AdrTunnelResult;
  /** Vehicle equipment per 8.1.4/8.1.5 — road only. */
  adr_equipment?: AdrEquipmentResult;
  /** Placarding and marking per ADR 5.3 — road only. */
  adr_placarding?: AdrPlacardingResult;
  adn_placarding?: AdnPlacardingResult;
  rid_placarding?: RidPlacardingResult;
  imdg_placarding?: ImdgPlacardingResult;
  /** High consequence dangerous goods per ADR 1.10.3 — road only. */
  adr_security?: AdrSecurityResult;
  q_values?: QValueResult[];
  q_check_status?: QCheckStatus;
  cargo_aircraft_only_products?: string[];
}


/** The unit catalogue. Units, and which of them are obvious for which category,
 *  are maintained in one place — in the backend — so the interface does not
 *  overwrite the list with another. */
export interface UnitCatalogue {
  units: { code: string; symbol: string; dimension: "mass" | "volume" | "length" | "count" }[];
  /** The form a commodity travels in, with the part of a cubic metre that is material. */
  forms: { code: string; fill_factor: number }[];
  /** Per category the applicable forms, the default first. Empty means the form
   *  does not come into play: for gravel the stored density is already a bulk
   *  density and a second factor would count the air twice. */
  forms_by_category: Record<string, string[]>;
  suggested_by_category: Record<string, string[]>;
  default_suggested: string[];
  density_basis_by_category: Record<string, string>;
}

export interface UnitConversion {
  mass_kg: number | null;
  volume_m3: number | null;
  density_basis: string;
  /** Filled when one of the two could not be determined, for example "per_item"
   *  with a count and no weight per item. Not an error but an outcome. */
  missing: string | null;
}


export type OrganisationSettings = Pick<InstanceSettings, "organisation_name" | "organisation_address" | "default_language" | "default_theme">;
export interface DgReview {
  id: string;
  reference: string;
  modality: string;
  status: "pending" | "approved" | "changes_requested";
  created_by: string;
  created_at: string;
  reviewed_by: string;
  reviewed_at: string | null;
  comment: string;
}
