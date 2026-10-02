import { primaryButton, secondaryButton } from "./buttons";

export default function Hero() {
  return (
    <header className="flex flex-col gap-6">
      <h1 className="font-display text-[76px] font-bold leading-[0.98] tracking-[-0.03em]">
        I build Python backends on AWS.
      </h1>
      <p className="text-xl leading-relaxed text-ink-soft">
        This side is my portfolio. The other side is what my backend sees while
        you read it.
      </p>
      <div className="flex flex-wrap gap-3.5">
        {/* Wired to a Lambda function in the backend phase */}
        <button type="button" className={primaryButton}>
          Download resume
        </button>
        <a href="mailto:you@example.com" className={secondaryButton}>
          Get in touch
        </a>
      </div>
    </header>
  );
}
