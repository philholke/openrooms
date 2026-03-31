import { cn } from "@/lib/utils";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

export function Card({ children, className, onClick }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-gray-200 bg-white p-4 shadow-sm",
        onClick && "cursor-pointer hover:border-gray-300 hover:shadow-md transition-shadow focus:outline-none focus:ring-2 focus:ring-gray-300",
        className
      )}
      onClick={onClick}
      {...(onClick ? {
        role: "button",
        tabIndex: 0,
        onKeyDown: (e: React.KeyboardEvent) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onClick();
          }
        },
      } : {})}
    >
      {children}
    </div>
  );
}
