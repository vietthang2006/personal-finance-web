import { forwardRef, useId } from "react";

const Input = forwardRef(function Input(
  { label, error, id, className = "", ...props },
  ref
) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const errorId = `${inputId}-error`;

  return (
    <div className="mb-4 flex flex-col gap-1">
      {label && (
        <label htmlFor={inputId} className="text-sm font-medium">
          {label}
        </label>
      )}
      <input
        ref={ref}
        id={inputId}
        className={[
          "rounded-lg border bg-white px-3 py-2",
          "focus:outline-2 focus:-outline-offset-1 focus:outline-blue-600",
          error ? "border-red-600" : "border-gray-300",
          className,
        ]
          .filter(Boolean)
          .join(" ")}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        {...props}
      />
      {error && (
        <small id={errorId} role="alert" className="text-sm text-red-600">
          {error}
        </small>
      )}
    </div>
  );
});

export default Input;