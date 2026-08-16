export interface Timestamped {
  id: string;
  created_at: string;
  updated_at: string;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
  pages: number;
}

export interface Paginated<T> {
  items: T[];
  meta: PaginationMeta;
}

export interface Permission {
  id: string;
  key: string;
  description: string;
}

export interface Role extends Timestamped {
  name: string;
  description: string | null;
  is_system: boolean;
  permissions: Permission[];
}

export interface UserBrief {
  id: string;
  username: string;
  first_name: string;
  last_name: string;
  display_name: string;
  avatar_url: string | null;
  job_title: string | null;
  department: string | null;
  presence: Presence;
}

export type PresenceStatus = "available" | "away" | "do_not_disturb" | "offline";

export interface Presence {
  status: PresenceStatus;
  manual_status: PresenceStatus | null;
  technical_status: "available" | "away" | "offline";
  status_message: string | null;
  status_until: string | null;
  last_seen_at: string | null;
  is_online: boolean;
}

export interface User extends Timestamped, UserBrief {
  email: string;
  is_active: boolean;
  last_login: string | null;
  roles: Pick<Role, "id" | "name">[];
}

export interface AuthUser extends User {
  bio: string | null;
  timezone: string;
  locale: string | null;
  permissions: string[];
}

export type ContactType = "email" | "phone" | "mobile";
export type ContactVisibility = "private" | "teams" | "organization";

export interface UserContact extends Timestamped {
  type: ContactType;
  label: string;
  value: string;
  is_primary: boolean;
  visibility: ContactVisibility;
}

export interface UserProfile extends UserBrief {
  bio: string | null;
  contacts: UserContact[];
  teams: { id: string; name: string }[];
  projects: { id: string; name: string }[];
}

export interface Team extends Timestamped {
  name: string;
  description: string | null;
  members: UserBrief[];
}

export interface Project extends Timestamped {
  name: string;
  key: string;
  description: string | null;
  status: string;
  start_date: string | null;
  end_date: string | null;
  teams: Pick<Team, "id" | "name">[];
}

export interface KanbanColumn extends Timestamped {
  project_id: string;
  name: string;
  key: string;
  position: number;
  is_done: boolean;
}

export interface Task extends Timestamped {
  project_id: string;
  number: number;
  reference: string;
  title: string;
  description: string | null;
  status: string;
  type: "task" | "story" | "bug" | "epic";
  priority: "lowest" | "low" | "medium" | "high" | "highest";
  assignee: UserBrief | null;
  reporter: UserBrief;
  sprint_id: string | null;
  kanban_column_id: string | null;
  position: number;
  due_date: string | null;
}

export interface Board {
  columns: KanbanColumn[];
  tasks: Task[];
}

export interface Sprint extends Timestamped {
  project_id: string;
  name: string;
  goal: string | null;
  start_date: string | null;
  end_date: string | null;
  status: "planned" | "active" | "completed" | "cancelled";
  tasks: Task[];
}

export interface Document extends Timestamped {
  project_id: string;
  title: string;
  slug: string;
  markdown_content: string;
  parent_id: string | null;
  created_by: UserBrief;
  updated_by: UserBrief;
}

export interface MeetingParticipant {
  user: UserBrief;
  response: string;
}

export interface Meeting extends Timestamped {
  title: string;
  description: string | null;
  start: string;
  end: string;
  location: string | null;
  meeting_url: string | null;
  creator: UserBrief;
  scope_type: string;
  scope_id: string | null;
  participants: MeetingParticipant[];
}

export interface CalendarItem {
  id: string;
  title: string;
  description: string | null;
  start: string;
  end: string;
  all_day: boolean;
  location: string | null;
  scope_type: string;
  scope_id: string | null;
  source: "event" | "meeting";
  creator?: UserBrief;
  participants?: MeetingParticipant[];
}

export interface CalendarFeed {
  items: CalendarItem[];
  available_sources: { key: string; label: string; type: string }[];
}

export interface PersonalDashboard {
  projects: Project[];
  teams: Team[];
  tasks: Task[];
  active_sprints: Sprint[];
  upcoming_meetings: Meeting[];
  upcoming_events: CalendarItem[];
}

export interface ProjectOverview {
  tasks: Task[];
  active_sprint: Sprint | null;
  upcoming_meetings: Meeting[];
  recent_documents: Document[];
  member_count: number;
}

export interface ApiErrorBody {
  error: { code: string; message: string; fields?: Record<string, string[]> };
  request_id?: string;
}
