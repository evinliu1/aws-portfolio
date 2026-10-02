import Hero from "./components/Hero";
import About from "./components/About";
import Skills from "./components/Skills";
import BehindTheScenes from "./components/BehindTheScenes";
import MobileNotice from "./components/MobileNotice";
import useIsDesktop from "./hooks/useIsDesktop";

export default function App() {
  const isDesktop = useIsDesktop();

  if (!isDesktop) {
    return <MobileNotice />;
  }

  return (
    <div className="grid min-h-screen grid-cols-[3fr_2fr]">
      <main className="flex flex-col gap-18 px-16 pb-24 pt-18 *:max-w-150">
        <div className="font-display text-xl font-bold">Evin Liu</div>
        <Hero />
        <About />
        <Skills />
      </main>
      <BehindTheScenes />
    </div>
  );
}
