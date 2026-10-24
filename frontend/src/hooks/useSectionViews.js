import { useEffect } from "react";

// Calls onView(id, heading) when a <section id="..."> inside the container is mostly on screen:
// at least 60% of a short section, or half the screen's height for a section taller than that.
export default function useSectionViews(containerRef, onView, enabled) {
  useEffect(() => {
    const container = containerRef.current;
    if (!enabled || !container) return;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const visibleHeight = entry.intersectionRect.height;
          const mostlyVisible =
            visibleHeight >= entry.boundingClientRect.height * 0.6 ||
            visibleHeight >= window.innerHeight * 0.5;
          if (entry.isIntersecting && mostlyVisible) {
            const section = entry.target;
            const heading = section.querySelector("h2")?.textContent ?? section.id;
            onView(section.id, heading);
          }
        }
      },
      { threshold: [0, 0.25, 0.5, 0.6, 0.75, 1] }
    );

    container.querySelectorAll("section[id]").forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, [containerRef, onView, enabled]);
}
