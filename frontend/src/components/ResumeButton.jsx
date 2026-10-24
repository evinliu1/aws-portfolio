import { useState } from "react";

const labels = {
  loading: "Preparing download…",
  error: "Download failed. Try again",
};

export default function ResumeButton({ onDownload, className, children }) {
  const [state, setState] = useState("idle");

  async function handleClick() {
    setState("loading");
    try {
      await onDownload();
      setState("idle");
    } catch {
      setState("error");
    }
  }

  return (
    <button
      type="button"
      data-track="download-resume"
      className={className}
      onClick={handleClick}
      disabled={state === "loading"}
      aria-live="polite"
    >
      {labels[state] ?? children}
    </button>
  );
}
