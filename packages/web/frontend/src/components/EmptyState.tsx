import React from "react";
import Icon, { type IconName } from "./Icon";

interface EmptyStateProps {
  icon?: IconName;
  title: string;
  hint?: string;
  action?: { label: string; onClick: () => void };
}

export default function EmptyState({ icon = "layers", title, hint, action }: EmptyStateProps) {
  return (
    <div className="empty">
      <Icon className="empty__icon" name={icon} size={34} strokeWidth={1.4} />
      <p className="empty__title">{title}</p>
      {hint && <p className="empty__hint">{hint}</p>}
      {action && (
        <button className="btn btn--primary" onClick={action.onClick}>
          {action.label}
        </button>
      )}
    </div>
  );
}
