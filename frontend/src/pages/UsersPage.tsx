import { ROLES, roleLabel, canManageAccount } from "../permissions";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { api, type Department, type User } from "../api/client";
import { usePreferences } from "../settings/preferences";
import { useToast } from "../toast/ToastProvider";
import ConfirmDialog from "../toast/ConfirmDialog";
import Avatar from "../components/Avatar";
import DeliveryAccountRoles from "../components/DeliveryAccountRoles";
import { PlusIcon, PenIcon, SearchIcon, CloseIcon, UserIcon, ShieldIcon, TrashIcon } from "../components/icons";

const inputClass = "directory-input";
const panelClass = "surface";
const buttonPrimary = "action-primary";
const buttonSecondary = "action-secondary";
type EditorFeedback = { kind: "error" | "success"; text: string } | null;

function guarded(target: User, self: User | null, users: User[]): string | null {
  if (self?.id === target.id) return "self";
  if (target.role === "admin" && target.active !== false && users.filter(u => u.role === "admin" && u.active !== false).length <= 1) return "lastAdmin";
  return null;
}

export default function UsersPage({ user: self }: { user: User | null }) {
  const { t } = useTranslation();
  const toast = useToast();
  const { publicSettings } = usePreferences();
  const historyOn = !!publicSettings?.history_enabled;
  const [users, setUsers] = useState<User[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [query, setQuery] = useState("");
  const [role, setRole] = useState("");
  const [status, setStatus] = useState("");
  const [section, setSection] = useState("users");
  const [editing, setEditing] = useState<number | "new" | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [feedback, setFeedback] = useState<EditorFeedback>(null);
  const active = useRef(false);

  async function load() {
    setLoading(true); setFailed(false);
    try { setUsers(await api.listUsers()); }
    catch (error) { setFailed(true); toast.error(String(error)); }
    finally { setLoading(false); }
  }
  async function loadDepartments() {
    try { setDepartments(await api.departments()); }
    catch (error) { toast.error(String(error)); }
  }
  useEffect(() => { void load(); }, []);
  useEffect(() => { if (historyOn) void loadDepartments(); }, [historyOn]);

  async function run(action: () => Promise<unknown>, message = ""): Promise<boolean> {
    if (active.current) return false;
    active.current = true; setBusy(true); setFeedback(null);
    try {
      await action(); await load();
      if (message) { toast.success(message); setFeedback({ kind: "success", text: message }); }
      return true;
    }
    catch (error) {
      setFeedback({ kind: "error", text: String(error) });
      return false;
    }
    finally { active.current = false; setBusy(false); }
  }
  function openEditor(id: number | "new") { setFeedback(null); setEditing(id); }
  function remove(target: User) {
    setEditing(null);
    setUsers(current => current.filter(u => u.id !== target.id));
    toast.undoable(t("toast.deletedUser", { name: target.username }), {
      execute: () => { api.deleteUser(target.id).then(load).catch(error => { toast.error(String(error)); void load(); }); },
      restore: () => setUsers(current => current.some(u => u.id === target.id) ? current : [...current, target]),
    });
  }
  const shown = useMemo(() => users.filter(u => {
    const text = [u.username, u.email, departments.find(d => d.id === u.department_id)?.name || ""].join(" ").toLocaleLowerCase();
    return text.includes(query.trim().toLocaleLowerCase()) && (!role || u.role === role)
      && (!status || (status === "active" ? u.active !== false : u.active === false));
  }), [users, departments, query, role, status]);
  const target = typeof editing === "number" ? users.find(u => u.id === editing) : undefined;

  return <div className="collection-page page-enter users-workspace">
    <header className="page-heading"><div><h2>{t("users.title")}</h2></div>
      <button type="button" className="action-primary" disabled={busy || loading || failed} onClick={() => openEditor("new")}><PlusIcon />{t("users.newUser")}</button>
    </header>
    {historyOn && <nav className="directory-sections" aria-label={t("users.title")}>
      <button type="button" aria-pressed={section === "users"} onClick={() => setSection("users")}>{t("users.title")}<span>{users.length}</span></button>
      <button type="button" aria-pressed={section === "departments"} onClick={() => setSection("departments")}>{t("departments.title")}<span>{departments.length}</span></button>
    </nav>}
    {section === "departments" && historyOn ? <DepartmentsPanel departments={departments} reload={loadDepartments} busy={busy} /> : <section className="surface directory-surface">
      <div className="directory-toolbar">
        <label className="directory-search"><SearchIcon /><span className="sr-only">{t("directory.search")}</span><input type="search" value={query} placeholder={t("directory.search")} onChange={e => setQuery(e.target.value)} /></label>
        <label><span className="sr-only">{t("users.role")}</span><select className={inputClass} value={role} onChange={e => setRole(e.target.value)}><option value="">{t("directory.allRoles")}</option>{ROLES.map(value => <option key={value} value={value}>{t(roleLabel(value))}</option>)}</select></label>
        <label><span className="sr-only">{t("directory.status")}</span><select className={inputClass} value={status} onChange={e => setStatus(e.target.value)}><option value="">{t("directory.allStatuses")}</option><option value="active">{t("directory.active")}</option><option value="inactive">{t("users.inactive")}</option></select></label>
      </div>
      <p className="directory-count" role="status">{loading ? t("wizard.loading") : t("directory.count", { shown: shown.length, total: users.length })}</p>
      {failed ? <div className="directory-empty" role="alert"><p>{t("directory.loadFailed")}</p><button type="button" className="action-secondary" onClick={() => void load()}>{t("historyAccess.retry")}</button></div>
        : !loading && !shown.length ? <div className="directory-empty"><UserIcon className="h-8 w-8" /><p>{t(users.length ? "directory.noResults" : "directory.empty")}</p></div>
        : <ul className="directory-list">{shown.map(u => <li className="directory-row" key={u.id}>
          <div className="directory-identity"><Avatar user={u} /><div><p><strong>{u.username}</strong>{u.id === self?.id && <span className="directory-you">{t("users.you")}</span>}</p><span className="directory-email">{u.email}</span></div></div>
          <div className="directory-membership"><span className={`directory-role ${u.role === "admin" ? "is-admin" : ""}`}>{u.role === "admin" && <ShieldIcon />}{t(roleLabel(u.role))}</span>{historyOn && <span>{departments.find(d => d.id === u.department_id)?.name || t("departments.none")}</span>}</div>
          <span className="directory-state" data-active={u.active !== false}>{t(u.active === false ? "users.inactive" : "directory.active")}</span>
          <button type="button" className="action-secondary directory-edit" aria-label={`${t("directory.edit")} ${u.username}`} disabled={busy || !canManageAccount(self, u)} title={!canManageAccount(self, u) ? t("roles.protected") : undefined} onClick={() => openEditor(u.id)}><PenIcon /><span>{t("directory.edit")}</span></button>
        </li>)}</ul>}
    </section>}
    {editing !== null && (editing === "new" || target) && <UserEditor key={editing} target={target} self={self} guard={target ? guarded(target, self, users) : null}
      departments={departments} historyOn={historyOn} canInvite={!!publicSettings?.mail_enabled} busy={busy} feedback={feedback} run={run} onClose={() => setEditing(null)} onRemove={remove} />}
  </div>;
}

function EditorDialog({ title, busy, onClose, children }: { title: string; busy: boolean; onClose: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  const closeRef = useRef(onClose); closeRef.current = onClose;
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const dialog = ref.current;
    dialog?.showModal();
    return () => { dialog?.close(); previous?.focus(); };
  }, []);
  const { t } = useTranslation();
  return <dialog ref={ref} className="user-editor" aria-label={title} onCancel={event => { event.preventDefault(); if (!busy) closeRef.current(); }}>
    <header><h2>{title}</h2><button type="button" className="action-quiet" disabled={busy} aria-label={t("directory.close")} onClick={onClose}><CloseIcon /></button></header>
    {children}
  </dialog>;
}

function UserEditor({ target, self, guard, departments, historyOn, canInvite, busy, feedback, run, onClose, onRemove }: {
  target?: User; self: User | null; guard: string | null; departments: Department[]; historyOn: boolean; canInvite: boolean; busy: boolean;
  feedback: EditorFeedback;
  run: (action: () => Promise<unknown>, message?: string) => Promise<boolean>; onClose: () => void; onRemove: (user: User) => void;
}) {
  const { t } = useTranslation();
  const toast = useToast();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState(target?.email || "");
  const [role, setRole] = useState(target?.role || "user");
  const [active, setActive] = useState(target?.active !== false);
  const [department, setDepartment] = useState(String(target?.department_id ?? ""));
  const [password, setPassword] = useState("");
  const [invite, setInvite] = useState(true);
  const [clearFactor, setClearFactor] = useState(false);
  const guardText = guard === "self" ? t("users.guardSelf") : guard ? t("users.guardLastAdmin") : "";
  const sendInvite = !target && canInvite && invite;

  async function save(event: React.FormEvent) {
    event.preventDefault();
    const success = await run(async () => {
      if (target) await api.updateUser(target.id, { email, role, active, ...(historyOn ? { department_id: department ? Number(department) : null } : {}) });
      else {
        const created = await api.createUser({ username, email, role, password: sendInvite ? undefined : password, send_welcome: sendInvite });
        if (sendInvite) {
          if (created.welcome_mail === "sent") toast.success(t("users.invited", { email }));
          else toast.error(t(created.welcome_mail === "no_mail_server" ? "users.inviteNoMailServer" : "users.inviteFailed", { reason: created.welcome_mail }));
        }
      }
    }, target ? t("users.saved") : sendInvite ? "" : t("users.created"));
    if (success) onClose();
  }
  return <EditorDialog title={t(target ? "directory.editTitle" : "users.newUser")} busy={busy} onClose={onClose}>
    {target && <div className="editor-identity"><Avatar user={target} large /><div><strong>{target.username}</strong><p>{target.id === self?.id ? t("users.you") : t(roleLabel(target.role))}</p></div></div>}
    {feedback && <p className="editor-feedback" data-kind={feedback.kind} role={feedback.kind === "error" ? "alert" : "status"}>{feedback.text}</p>}
    <form className="editor-form" onSubmit={event => void save(event)}>
      {!target && <label>{t("users.username")}<input className={inputClass} value={username} minLength={3} maxLength={64} required autoComplete="off" onChange={e => setUsername(e.target.value)} /></label>}
      <label>{t("users.email")}<input className={inputClass} type="email" value={email} required onChange={e => setEmail(e.target.value)} /></label>
      <div className="editor-fields"><label>{t("users.role")}<select className={inputClass} value={role} disabled={busy || !!guard} title={guardText} onChange={e => setRole(e.target.value)}>{ROLES.filter(value => self?.role === "admin" || ["user", "shipment", "planner", "operator", "recipient", "super_user"].includes(value)).map(value => <option key={value} value={value}>{t(roleLabel(value))}</option>)}</select></label>
        {historyOn && target && <label>{t("departments.userDepartment")}<select className={inputClass} value={department} onChange={e => setDepartment(e.target.value)}><option value="">{t("departments.none")}</option>{departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</select></label>}
      </div>
      {target && <label className="editor-toggle"><input type="checkbox" checked={active} disabled={busy || !!guard} onChange={e => setActive(e.target.checked)} /><span>{t("directory.activeAccount")}</span></label>}
      {guardText && <p className="editor-hint">{guardText}</p>}
      {!target && canInvite && <label className="editor-toggle"><input type="checkbox" checked={invite} onChange={e => setInvite(e.target.checked)} /><span>{t("users.invite")}</span></label>}
      {!target && !sendInvite && <label>{t("users.password")}<input className={inputClass} type="password" value={password} minLength={8} required autoComplete="new-password" placeholder={t("users.passwordHint")} onChange={e => setPassword(e.target.value)} /></label>}
      <footer><button type="button" className="action-secondary" disabled={busy} onClick={onClose}>{t("toast.cancel")}</button><button className="action-primary" disabled={busy}>{t(busy ? "directory.saving" : target ? "directory.save" : sendInvite ? "users.createAndInvite" : "users.create")}</button></footer>
    </form>
    {target && historyOn && <DeliveryAccountRoles target={target} self={self} busy={busy} run={run} />}
    {target && <details className="editor-security"><summary><ShieldIcon />{t("directory.security")}</summary><div>
      <form className="editor-form" onSubmit={event => { event.preventDefault(); void run(() => api.updateUser(target.id, { password }), t("users.passwordReset")).then(ok => { if (ok) setPassword(""); }); }}>
        <label>{t("users.newPasswordFor", { name: target.username })}<input className={inputClass} type="password" value={password} minLength={8} required autoComplete="new-password" placeholder={t("users.passwordHint")} onChange={e => setPassword(e.target.value)} /></label>
        <button className="action-secondary" disabled={busy}>{t("users.resetPasswordDo")}</button>
      </form>
      <button type="button" className="action-secondary" disabled={busy} onClick={() => setClearFactor(true)}>{t("users.clearTwoFactor")}</button>
      <button type="button" className="editor-delete" disabled={busy || !!guard} title={guardText} onClick={() => onRemove(target)}><TrashIcon />{t("users.delete")}</button>
    </div></details>}
    <ConfirmDialog open={clearFactor} title={t("users.clearTwoFactor")} body={t("users.clearTwoFactorConfirm", { name: target?.username })} confirmLabel={t("users.clearTwoFactor")}
      onCancel={() => setClearFactor(false)} onConfirm={() => { setClearFactor(false); if (target) void run(() => api.clearTwoFactorFor(target.id), t("users.twoFactorCleared")); }} />
  </EditorDialog>;
}

/**
 * The departments themselves: add, rename, remove.
 *
 * Removing one leaves its people and shipments without a department rather
 * than deleting either — the dialog says so, because "remove" beside a count
 * of shipments reads as if the shipments go too.
 */
function DepartmentsPanel({
  departments,
  reload,
  busy,
}: {
  departments: Department[];
  reload: () => Promise<void>;
  busy: boolean;
}) {
  const { t } = useTranslation();
  const toast = useToast();
  const [name, setName] = useState("");
  const [renaming, setRenaming] = useState<Department | null>(null);
  const [newName, setNewName] = useState("");
  const [removing, setRemoving] = useState<Department | null>(null);
  const [working, setWorking] = useState(false);

  const act = async (work: () => Promise<unknown>, done: string) => {
    setWorking(true);
    try {
      await work();
      await reload();
      toast.success(done);
    } catch (e) {
      toast.error(String(e));
    } finally {
      setWorking(false);
    }
  };

  const add = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    void act(() => api.createDepartment(name.trim()), t("departments.saved")).then(() => setName(""));
  };

  return (
    <div className={`${panelClass} p-5 space-y-4`}>
      <div>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {t("departments.title")}
        </h3>
      </div>

      {departments.length === 0 && (
        <p className="text-sm text-slate-500 dark:text-slate-400">{t("departments.empty")}</p>
      )}
      <ul className="divide-y divide-slate-100 dark:divide-slate-800">
        {departments.map((d) => (
          <li key={d.id} className="flex flex-wrap items-center gap-2 py-2">
            {renaming?.id === d.id ? (
              <form
                className="flex flex-1 flex-wrap items-center gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  void act(() => api.renameDepartment(d.id, newName.trim()), t("departments.saved")).then(() =>
                    setRenaming(null),
                  );
                }}
              >
                <input
                  className={`${inputClass} !w-auto flex-1 py-1.5 text-sm`}
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  aria-label={t("departments.name")}
                  autoFocus
                />
                <button className={buttonPrimary} disabled={working || !newName.trim()}>
                  {t("departments.save")}
                </button>
                <button type="button" className={buttonSecondary} onClick={() => setRenaming(null)}>
                  {t("departments.cancel")}
                </button>
              </form>
            ) : (
              <>
                <span className="font-medium text-slate-900 dark:text-slate-100">{d.name}</span>
                <span className="text-xs text-slate-500 dark:text-slate-400">
                  {t("departments.counts", { users: d.users, shipments: d.shipments })}
                </span>
                <div className="ml-auto flex gap-2">
                  <button
                    type="button"
                    className={buttonSecondary}
                    disabled={busy || working}
                    onClick={() => {
                      setRenaming(d);
                      setNewName(d.name);
                    }}
                  >
                    {t("departments.rename")}
                  </button>
                  <button
                    type="button"
                    className={buttonSecondary}
                    disabled={busy || working}
                    onClick={() => setRemoving(d)}
                  >
                    {t("departments.remove")}
                  </button>
                </div>
              </>
            )}
          </li>
        ))}
      </ul>

      <form onSubmit={add} className="flex flex-wrap items-end gap-2">
        <div className="min-w-[200px] flex-1">
          <label className="text-xs text-slate-500 dark:text-slate-400" htmlFor="new-department">
            {t("departments.name")}
          </label>
          <input
            id="new-department"
            className={`${inputClass} mt-1`}
            value={name}
            maxLength={80}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <button className={buttonPrimary} disabled={working || !name.trim()}>
          {t("departments.add")}
        </button>
      </form>

      <ConfirmDialog
        open={removing !== null}
        title={t("departments.remove")}
        body={removing ? t("departments.confirmRemove", { name: removing.name }) : ""}
        confirmLabel={t("departments.remove")}
        onConfirm={() => {
          const target = removing;
          setRemoving(null);
          if (target) void act(() => api.deleteDepartment(target.id), t("departments.removed"));
        }}
        onCancel={() => setRemoving(null)}
      />
    </div>
  );
}
