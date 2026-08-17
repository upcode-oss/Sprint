import * as React from "react";

import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => <input ref={ref} className={cn("input", className)} {...props} />,
);
Input.displayName = "Input";

export const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => (
  <textarea ref={ref} className={cn("input textarea", className)} {...props} />
));
Textarea.displayName = "Textarea";

export const Select = React.forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, ...props }, ref) => <select ref={ref} className={cn("input select", className)} {...props} />,
);
Select.displayName = "Select";

export function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string;
  hint?: string;
  error?: string;
  children: React.ReactNode;
}) {
  const fieldId = React.useId();
  const descriptionId = `${fieldId}-description`;
  const labelId = `${fieldId}-label`;
  const childItems = React.Children.toArray(children);
  const firstChild = childItems[0];
  const isCompositeLabel = React.isValidElement(firstChild) && firstChild.type === "label";
  const describedChildren = childItems.map((child, index) => {
    if (index !== 0 || isCompositeLabel || !React.isValidElement<Record<string, unknown>>(child)) return child;
    const existingDescription = child.props["aria-describedby"];
    return React.cloneElement(child, {
      id: child.props.id ?? fieldId,
      "aria-describedby": [existingDescription, hint || error ? descriptionId : undefined].filter(Boolean).join(" ") || undefined,
      "aria-invalid": error ? true : child.props["aria-invalid"],
    });
  });

  return (
    <div className="field" role={isCompositeLabel ? "group" : undefined} aria-labelledby={isCompositeLabel ? labelId : undefined}>
      {isCompositeLabel ? <span className="field-label" id={labelId}>{label}</span> : <label className="field-label" htmlFor={fieldId}>{label}</label>}
      {describedChildren}
      {error ? <span className="field-error" id={descriptionId} role="alert">{error}</span> : hint ? <span className="field-hint" id={descriptionId}>{hint}</span> : null}
    </div>
  );
}
