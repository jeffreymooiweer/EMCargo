import type { PublicSettings, User } from "./api/client";
export const ROLES = ["user", "shipment", "planner", "operator", "recipient", "assessor", "super_user", "dg_specialist", "admin"] as const;
export const roleLabel = (role: string) => ({ admin: "users.roleAdmin", user: "users.roleUser", super_user: "roles.superUser", dg_specialist: "roles.dgSpecialist" }[role] || `deliveries.roles.${role}`);
export const canManage = (user?: User | null) => !!user && ["admin", "super_user"].includes(user.role);
export const canOversee = (user?: User | null) => !!user && ["admin", "super_user", "dg_specialist"].includes(user.role);
export const canManageAccount = (actor: User | null, target: User) => actor?.role === "admin" || (actor?.role === "super_user" && ["user", "shipment", "planner", "operator", "recipient", "external", "super_user"].includes(target.role));
export const canUseDgsa = (user?: User | null, settings?: PublicSettings | null) => !!user && (["admin", "dg_specialist"].includes(user.role) || (user.role === "super_user" && settings?.super_user_dgsa_enabled === true));
