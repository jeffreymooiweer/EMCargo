import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { User } from "../api/client";
import { deliveries, modes, type Mode } from "../api/deliveries";

const taskRoles = ["shipment", "planner", "operator", "recipient", "assessor"];

export default function DeliveryAccountRoles({ target, self, busy, run }: {
  target: User; self: User | null; busy: boolean;
  run: (action: () => Promise<unknown>, message?: string) => Promise<boolean>;
}) {
  const { t } = useTranslation();
  const [roles, setRoles] = useState<string[]>([]);
  const [competence, setCompetence] = useState<Mode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    deliveries.account(target.id).then(profile => {
      if (active) { setRoles(profile.roles); setCompetence(profile.modes); }
    }).catch(reason => { if (active) setError(String(reason)); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [target.id]);
  const limited = ["operator", "recipient", "external"].includes(target.role);
  return <details className="editor-security"><summary>{t("deliveries.taskRoles")}</summary>
    <p className="editor-hint">{t("deliveries.taskRolesHint")}</p>
    {error && <p role="alert">{error}</p>}
    <fieldset className="editor-form" disabled={busy || loading || !!error}>
      {taskRoles.filter(role => !limited || ["operator", "recipient"].includes(role)).map(role => <label key={role} className="editor-toggle">
        <input type="checkbox" checked={roles.includes(role)} disabled={role === "assessor" && self?.role !== "admin"}
          onChange={event => setRoles(current => event.target.checked ? [...current, role] : current.filter(item => item !== role))} />
        <span>{t(`deliveries.roles.${role}`)}</span>
      </label>)}
      {roles.includes("assessor") && <fieldset disabled={self?.role !== "admin"}><legend>{t("deliveries.competence")}</legend>
        {modes.map(mode => <label key={mode} className="editor-toggle"><input type="checkbox" checked={competence.includes(mode)}
          onChange={event => setCompetence(current => event.target.checked ? [...current, mode] : current.filter(item => item !== mode))} /><span>{t(`deliveries.modes.${mode}`)}</span></label>)}
      </fieldset>}
      <button type="button" className="action-secondary" onClick={() => void run(() => deliveries.saveAccount(target.id, roles, roles.includes("assessor") ? competence : []), t("deliveries.saved"))}>{t("deliveries.saveRoles")}</button>
    </fieldset>
  </details>;
}
