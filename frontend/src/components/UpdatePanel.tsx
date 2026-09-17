import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, InstanceSettings, UpdateCapability, UpdateStateAnswer, UpdateStatus } from "../api/client";
import ConfirmDialog from "../toast/ConfirmDialog";
import { useToast } from "../toast/ToastProvider";
import { CheckIcon, DownloadIcon, RefreshIcon, WarningIcon } from "./icons";

const IN_PROGRESS = ["pulling", "handed_over", "stopping"];

/** An update is a persistent operation. Returning to this screen resumes its
 * progress; leaving it cancels only the observer, never the server operation. */
export default function UpdatePanel() {
  const { t } = useTranslation();
  const toast = useToast();
  const [capability, setCapability] = useState<UpdateCapability | null>(null);
  const [status, setStatus] = useState<UpdateStatus | null>(null);
  const [instance, setInstance] = useState<InstanceSettings | null>(null);
  const [state, setState] = useState<UpdateStateAnswer["state"]>(null);
  const [error, setError] = useState("");
  const [checking, setChecking] = useState(false);
  const [changing, setChanging] = useState(false);
  const [applying, setApplying] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [target, setTarget] = useState<string | null>(null);
  const observedVersion = useRef("");
  const mounted = useRef(false);
  const requestId = useRef(0);
  const submitting = useRef(false);

  useEffect(() => {
    mounted.current = true;
    let cancelled = false;
    void Promise.allSettled([api.updateCapability(), api.updateStatus(), api.updateState(), api.instanceSettings()])
      .then(([ability, release, progress, settings]) => {
        if (cancelled) return;
        if (ability.status === "fulfilled") setCapability(ability.value);
        if (release.status === "fulfilled") setStatus(release.value);
        if (settings.status === "fulfilled") setInstance(settings.value);
        if (progress.status === "fulfilled") {
          observedVersion.current = progress.value.current;
          setState(progress.value.state);
          if (progress.value.state && IN_PROGRESS.includes(progress.value.state.phase)) {
            const nextVersion = progress.value.state.to || progress.value.state.to_image?.split(":").pop() || "";
            // The helper can still be finishing its health check, or have left
            // stale progress behind. A page already on that version must not
            // resume the observer and reload itself on every mount.
            if (nextVersion !== progress.value.current) {
              setTarget(nextVersion);
              setApplying(true);
            }
          }
        }
        const failed = [ability, release, progress, settings].find((result) => result.status === "rejected");
        if (failed?.status === "rejected") setError(String(failed.reason));
      });
    return () => { cancelled = true; mounted.current = false; requestId.current += 1; };
  }, []);

  useEffect(() => {
    if (!applying || target === null) return;
    let cancelled = false;
    let timer: number;
    const started = Date.now();
    async function poll() {
      try {
        const answer = await api.updateState();
        if (cancelled) return;
        setState(answer.state);
        if (answer.state?.phase === "failed") { setApplying(false); return; }
        // The target must actually answer, even if an old completion record
        // remains. Older servers consume that record, so it may also be absent.
        if (target ? answer.current === target : answer.state?.phase === "done") {
          setApplying(false);
          if (answer.current !== observedVersion.current) window.location.reload();
          return;
        }
      } catch {
        if (cancelled) return;
        setState((previous) => ({ ...previous, phase: "stopping" }));
      }
      if (Date.now() - started >= 12 * 60 * 1000) {
        setError(t("settings.updateTimeout"));
        setApplying(false);
      } else timer = window.setTimeout(poll, 2500);
    }
    timer = window.setTimeout(poll, 1500);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [applying, target, t]);

  async function checkNow() {
    const id = ++requestId.current;
    setChecking(true); setError("");
    try {
      const [release, ability] = await Promise.all([api.updateCheckNow(), api.updateCapability()]);
      if (mounted.current && id === requestId.current) { setStatus(release); setCapability(ability); }
    } catch (exception) { if (mounted.current && id === requestId.current) setError(String(exception)); }
    finally { if (mounted.current && id === requestId.current) setChecking(false); }
  }

  async function toggleCheck() {
    if (!instance || changing) return;
    setChanging(true); setError("");
    try {
      // Read again before changing the single switch, preserving settings
      // another administrator might have saved since this screen opened.
      const current = await api.instanceSettings();
      const answer = await api.saveInstanceSettings({ ...current, update_check_enabled: !instance.update_check_enabled });
      if (!mounted.current) return;
      setInstance(answer);
      setStatus((previous) => previous ? { enabled: answer.update_check_enabled, current: previous.current } : null);
      toast.success(t("settings.saved"));
    } catch (exception) { if (mounted.current) setError(String(exception)); }
    finally { if (mounted.current) setChanging(false); }
  }

  async function apply() {
    if (submitting.current) return;
    submitting.current = true;
    setConfirm(false); setApplying(true); setError("");
    // Do not poll a previous attempt while this request is still pending.
    setTarget(null);
    observedVersion.current = status?.current || observedVersion.current;
    setState({ phase: "pulling", to: status?.latest });
    try {
      const answer = await api.updateApply();
      if (mounted.current) setTarget(answer.to);
    } catch (exception) {
      if (mounted.current) { setError(String(exception)); setApplying(false); setState(null); }
    } finally { submitting.current = false; }
  }

  const available = status?.update_available === true;
  const enabled = instance?.update_check_enabled ?? status?.enabled;
  const method = capability?.install_method || "docker";
  const reason = capability?.reason;
  const reasonKey = ({ no_socket: "settings.updateReasonNoSocket",
    socket_permission: "settings.updateReasonPermission", container_not_found: "settings.updateReasonContainerNotFound",
    socket_unusable: "settings.updateReasonSocketUnusable", foreign_image: "settings.updateReasonForeignImage",
    native: "settings.updateNative", kubernetes: "settings.updateKubernetes" } as Record<string, string>)[reason || ""];

  return <div className="updates-workspace">
    <section className="surface update-overview" aria-busy={checking || applying}>
      <div className="update-symbol"><RefreshIcon className={applying || checking ? "h-7 w-7 animate-spin" : "h-7 w-7"} /></div>
      <div className="update-heading"><p className="eyebrow">EMCargo</p><h3>{t("settings.adminUpdates")}</h3></div>
      <div className="update-versions">
        <div><span>{t("updates.installed")}</span><strong>{status?.current ? `v${status.current}` : "—"}</strong></div>
        <div><span>{t("updates.latest")}</span><strong>{status?.latest ? `v${status.latest}` : "—"}</strong></div>
      </div>
      <div className="update-status" role="status">
        {applying ? <><RefreshIcon className="h-4 w-4 animate-spin" />{t(state?.phase === "pulling" ? "settings.updatePhasePulling" : "settings.updatePhaseRestarting")}</>
          : available ? <><DownloadIcon />{t("update.available", { version: status?.latest })}</>
          : status?.reachable ? <><CheckIcon />{t("settings.updateUpToDate", { version: status.current })}</>
          : enabled === false ? t("updates.checkDisabled")
          : status?.reachable === false ? <><WarningIcon />{t("settings.updateUnreachable")}</>
          : t("updates.notChecked")}
      </div>
      {applying && <div className="update-progress" aria-hidden="true"><span /></div>}
      <div className="update-actions">
        {available && <button type="button" className="action-primary" onClick={() => setConfirm(true)}
          disabled={applying || !capability?.available || !enabled}><DownloadIcon />{t("settings.updateApplyNow", { version: status?.latest })}</button>}
        <button type="button" className={available ? "action-secondary" : "action-primary"} onClick={() => void checkNow()}
          disabled={checking || applying || enabled === false}><RefreshIcon />{t(checking ? "settings.updateChecking" : "settings.updateCheckNow")}</button>
        {status?.url && <a className="update-release-link" href={status.url} target="_blank" rel="noopener noreferrer">{t("update.releaseNotes")}</a>}
      </div>
      {error && <p className="update-error" role="alert">{error}</p>}
      {state?.phase === "failed" && <p className="update-error" role="alert">{t("settings.updateFailed", { error: state.error || "" })}</p>}
      {!applying && state?.phase === "done" && <p className="update-status" role="status">{t("settings.updateDone", { version: status?.current || "" })}</p>}
    </section>

    <section className="surface update-preferences">
      <label className="update-switch"><span><strong>{t("settings.updateCheck")}</strong></span>
        <input type="checkbox" role="switch" checked={enabled ?? false} disabled={!instance || changing || applying} onChange={() => void toggleCheck()} /></label>
      <div className="update-capability"><span className="update-capability-label">{t("updates.inApp")}</span>
        <strong>{t(capability?.available ? "updates.ready" : capability ? "updates.setupNeeded" : "updates.loadingCapability")}</strong></div>
      {reasonKey && <p className="update-reason">{t(reasonKey)}</p>}
      {capability && !capability.available && method !== "docker" && <details className="update-setup">
        <summary>{t("updates.setup")}</summary>
        <pre>{method === "native" ? "sudo /opt/emcargo/current/deploy/native/update.sh" : `kubectl -n emcargo set image deployment/emcargo emcargo=ghcr.io/jeffreymooiweer/emcargo:${status?.latest || "<version>"}`}</pre>
      </details>}
    </section>
    <ConfirmDialog tone="primary" open={confirm} title={t("settings.adminUpdates")}
      body={t("settings.updateApplyConfirm", { version: status?.latest || "" })}
      confirmLabel={t("settings.updateApplyNow", { version: status?.latest || "" })}
      onConfirm={() => void apply()} onCancel={() => setConfirm(false)} />
  </div>;
}
