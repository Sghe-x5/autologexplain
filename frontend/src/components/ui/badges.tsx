/**
 * Переиспользуемые badges для Severity / Status / AlertLevel.
 *
 * Вся цветовая легенда в одном месте (раньше дублировалась в OverviewPage,
 * IncidentsPage, IncidentDetails, SimilarIncidentsBlock через lib/format.ts).
 * Этот компонент + константы — единый источник правды.
 */

import type { IncidentSeverity, IncidentStatus } from "@/api/incidentsApi";
import type { AlertLevel } from "@/api/rcaApi";
import { cn } from "@/lib/utils";
import {
  alertLevelColors,
  alertLevelLabel,
  severityColors,
  statusColors,
  statusLabel,
} from "@/widgets/Dashboard/lib/format";

type Size = "sm" | "md";

const sizeClasses: Record<Size, string> = {
  sm: "text-[10px] px-1.5 py-0",
  md: "text-[11px] px-2 py-0.5",
};

export const SeverityBadge = ({
  value,
  size = "md",
  className,
}: {
  value: IncidentSeverity;
  size?: Size;
  className?: string;
}) => (
  <span
    className={cn(
      "rounded-md font-semibold uppercase",
      sizeClasses[size],
      severityColors[value],
      className
    )}
    data-test-id={`severity-badge-${value}`}
  >
    {value}
  </span>
);

export const StatusBadge = ({
  value,
  size = "md",
  className,
}: {
  value: IncidentStatus;
  size?: Size;
  className?: string;
}) => (
  <span
    className={cn(
      "rounded-md font-medium",
      sizeClasses[size],
      statusColors[value],
      className
    )}
    data-test-id={`status-badge-${value}`}
  >
    {statusLabel[value]}
  </span>
);

export const AlertLevelBadge = ({
  value,
  size = "md",
  className,
}: {
  value: AlertLevel;
  size?: Size;
  className?: string;
}) => (
  <span
    className={cn(
      "rounded-md font-semibold",
      sizeClasses[size],
      alertLevelColors[value],
      className
    )}
    data-test-id={`alert-badge-${value}`}
  >
    {alertLevelLabel[value]}
  </span>
);
