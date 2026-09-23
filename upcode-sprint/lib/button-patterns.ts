import type { LucideIcon } from "lucide-react";
import {
  Download,
  Edit,
  Filter,
  Pause,
  Play,
  Plus,
  RefreshCw,
  RotateCw,
  Save,
  Search,
  Settings,
  Square,
  Trash2,
  Upload,
  X,
} from "lucide-react";

export type ButtonPattern = {
  variant: "default" | "outline" | "destructive" | "ghost";
  icon: LucideIcon;
  loadingText?: string;
};

export const buttonPatterns = {
  create: { variant: "default", icon: Plus, loadingText: "Creating…" },
  add: { variant: "default", icon: Plus, loadingText: "Adding…" },
  save: { variant: "default", icon: Save, loadingText: "Saving…" },
  edit: { variant: "outline", icon: Edit },
  cancel: { variant: "outline", icon: X },
  delete: { variant: "destructive", icon: Trash2, loadingText: "Deleting…" },
  download: { variant: "outline", icon: Download, loadingText: "Downloading…" },
  upload: { variant: "outline", icon: Upload, loadingText: "Uploading…" },
  start: { variant: "default", icon: Play, loadingText: "Starting…" },
  stop: { variant: "destructive", icon: Square, loadingText: "Stopping…" },
  pause: { variant: "outline", icon: Pause },
  restart: { variant: "outline", icon: RotateCw, loadingText: "Restarting…" },
  search: { variant: "ghost", icon: Search },
  filter: { variant: "ghost", icon: Filter },
  settings: { variant: "ghost", icon: Settings },
  refresh: { variant: "ghost", icon: RefreshCw },
} satisfies Record<string, ButtonPattern>;

