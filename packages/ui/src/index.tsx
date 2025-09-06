import * as React from "react";

export function Button({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button {...props} className={`inline-flex items-center rounded px-3 py-2 text-sm font-medium bg-black text-white hover:opacity-90 ${props.className ?? ""}`}>
      {children}
    </button>
  );
}

