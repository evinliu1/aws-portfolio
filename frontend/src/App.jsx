import { useRef } from "react";
import Hero from "./components/Hero";
import About from "./components/About";
import Skills from "./components/Skills";
import BehindTheScenes from "./components/BehindTheScenes";
import MobileNotice from "./components/MobileNotice";
import useIsDesktop from "./hooks/useIsDesktop";
import useBackendSession from "./hooks/useBackendSession";
import useSectionViews from "./hooks/useSectionViews";

export default function App() {
  const isDesktop = useIsDesktop();
  const session = useBackendSession();
  const mainRef = useRef(null);
  useSectionViews(mainRef, session.viewSection, isDesktop && session.status === "live");

  if (!isDesktop) {
    return <MobileNotice session={session} />;
  }

  return (
    <div className="grid min-h-screen grid-cols-[3fr_2fr]">
      <main ref={mainRef} className="flex flex-col gap-18 px-16 pb-24 pt-18 *:max-w-150">
        <div className="font-display text-xl font-bold">Evin Liu</div>
        <Hero />
        <About />
        <Skills />
      </main>
      <BehindTheScenes session={session} />
    </div>
  );
}
