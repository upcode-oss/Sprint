import Image from "next/image";
import Link from "next/link";

import { initials } from "@/lib/utils";
import type { PresenceStatus, UserBrief } from "@/types/api";

const presenceLabels: Record<PresenceStatus, string> = {
  available: "Available",
  away: "Away",
  do_not_disturb: "Do not disturb",
  offline: "Offline",
};

export function UserAvatar({
  user,
  size = 32,
  showPresence = true,
}: {
  user: UserBrief;
  size?: number;
  showPresence?: boolean;
}) {
  const avatar = <span className="avatar-shell" style={{ height: size, width: size }}>
    {user.avatar_url ? <Image className="avatar-image" src={user.avatar_url} alt="" width={size} height={size} unoptimized /> : <span className="avatar" style={{ height: size, width: size }}>{initials(user.first_name, user.last_name)}</span>}
    {showPresence ? <span className={`presence-dot presence-${user.presence.status}`} title={presenceLabels[user.presence.status]}><span className="sr-only">{presenceLabels[user.presence.status]}</span></span> : null}
  </span>;
  return avatar;
}

export function UserIdentity({
  user,
  compact = false,
  linked = false,
}: {
  user: UserBrief;
  compact?: boolean;
  linked?: boolean;
}) {
  const content = <span className="user-identity">
    <UserAvatar user={user} size={compact ? 26 : 34} />
    <span className="user-identity-copy">
      <strong>{user.display_name}</strong>
      {!compact ? <span>{user.job_title || `@${user.username}`}</span> : null}
    </span>
  </span>;
  return linked ? <Link href={`/users/${user.id}`} className="user-identity-link">{content}</Link> : content;
}

export { presenceLabels };
