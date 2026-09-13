import { useState } from "react";
import type { User } from "../api/client";

export default function Avatar({ user, large = false }: { user: Pick<User, "username" | "avatar_url" | "display_name">; large?: boolean }) {
  const [failed, setFailed] = useState<string | null>(null);
  const label = user.display_name?.trim() || user.username;
  const words = label.split(/\s+/);
  const initials = (words.length > 1 ? `${words[0][0]}${words[words.length - 1][0]}` : label.slice(0, 2)).toUpperCase();
  return <span className={`profile-avatar ${large ? "profile-avatar-large" : ""}`} aria-hidden="true">
    {user.avatar_url && failed !== user.avatar_url
      ? <img src={user.avatar_url} alt="" onError={() => setFailed(user.avatar_url || null)} />
      : <span>{initials}</span>}
  </span>;
}
