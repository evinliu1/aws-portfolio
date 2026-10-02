import { useEffect, useState } from "react";

export default function useIsDesktop(minWidth = 1024) {
  const query = `(min-width: ${minWidth}px)`;
  const [matches, setMatches] = useState(
    () => window.matchMedia(query).matches
  );

  useEffect(() => {
    const mediaQuery = window.matchMedia(query);
    const onChange = (event) => setMatches(event.matches);
    mediaQuery.addEventListener("change", onChange);
    return () => mediaQuery.removeEventListener("change", onChange);
  }, [query]);

  return matches;
}
