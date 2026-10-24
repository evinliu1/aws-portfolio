import { useEffect } from "react";

// Calls onClick(id) whenever something inside a data-track="<id>" element is clicked.
export default function useClickTracking(onClick, enabled) {
  useEffect(() => {
    if (!enabled) return;

    function handleClick(event) {
      const tracked = event.target.closest?.("[data-track]");
      if (tracked) onClick(tracked.dataset.track);
    }

    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, [onClick, enabled]);
}
