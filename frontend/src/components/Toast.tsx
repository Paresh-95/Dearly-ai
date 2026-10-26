import { useEffect } from "react";

export default function Toast({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 6000);
    return () => clearTimeout(timer);
  }, [message, onDismiss]);

  return (
    <div className="toast">
      <span className="toast__text">{message}</span>
      <button type="button" className="toast__close" onClick={onDismiss} aria-label="Dismiss">
        &times;
      </button>
    </div>
  );
}
