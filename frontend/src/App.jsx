import Hero from "./components/Hero";
import About from "./components/About";
import Skills from "./components/Skills";
import Resume from "./components/Resume";
import BehindTheScenes from "./components/BehindTheScenes";
import "./App.css";

export default function App() {
  return (
    <div className="layout">
      <main>
        <Hero />
        <About />
        <Skills />
        <Resume />
      </main>
      <BehindTheScenes />
    </div>
  );
}
