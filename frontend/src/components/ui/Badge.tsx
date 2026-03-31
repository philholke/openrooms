import { cn } from "@/lib/utils";
import type { ReservationStatus, WaitlistStatus } from "@/lib/types";

type BadgeVariant = "default" | "success" | "warning" | "danger" | "info";

const variantStyles: Record<BadgeVariant, string> = {
  default: "bg-gray-100 text-gray-700",
  success: "bg-green-100 text-green-800",
  warning: "bg-yellow-100 text-yellow-800",
  danger: "bg-red-100 text-red-800",
  info: "bg-blue-100 text-blue-800",
};

const statusVariant: Record<ReservationStatus | WaitlistStatus, BadgeVariant> = {
  pending: "warning",
  confirmed: "info",
  arrived: "info",
  partially_arrived: "warning",
  seated: "success",
  completed: "default",
  no_show: "danger",
  cancelled: "danger",
  waiting: "warning",
  notified: "info",
};

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

export function Badge({ children, variant = "default", className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        variantStyles[variant],
        className
      )}
    >
      {children}
    </span>
  );
}

export function StatusBadge({
  status,
}: {
  status: ReservationStatus | WaitlistStatus;
}) {
  const variant = statusVariant[status] || "default";
  const label = status.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());

  return <Badge variant={variant}>{label}</Badge>;
}
