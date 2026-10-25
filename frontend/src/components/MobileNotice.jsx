import { useState } from "react";
import { primaryButton, secondaryButton } from "./buttons";
import ResumeButton from "./ResumeButton";

const deleteLabels = {
  idle: "Delete it now",
  deleting: "Deleting…",
  error: "The delete didn't go through. Try again",
};

export default function MobileNotice({ session }) {
  const [copied, setCopied] = useState(false);
  const [deleteState, setDeleteState] = useState("idle");

  async function deleteVisit() {
    setDeleteState("deleting");
    try {
      await session.deleteData(); // On success the status changes and this button goes away.
    } catch {
      setDeleteState("error");
    }
  }

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col">
      <div className="flex grow flex-col gap-7 px-6 pb-7 pt-10">
        <div className="font-display text-lg font-bold">Evin Liu</div>

        <div className="flex flex-col items-center" aria-hidden="true">
          <div className="flex h-34 w-55 gap-1 rounded-[10px] border-3 border-ink p-1.5">
            <div className="flex-3 rounded-sm bg-chip"></div>
            <div className="flex-2 rounded-sm bg-navy"></div>
          </div>
          <div className="h-2.5 w-65 rounded-b-lg bg-ink"></div>
        </div>

        <h1 className="font-display text-[40px] font-bold leading-[1.02] tracking-[-0.03em]">
          This one needs a bigger screen.
        </h1>
        <p className="text-[17px] leading-relaxed text-ink-soft">
          My site shows my portfolio side by side with a live view of its AWS
          backend. On a phone, the two sides don't fit. Open the link on a
          computer to see both.
        </p>

        <div className="flex flex-col gap-3">
          <button type="button" className={primaryButton} onClick={copyLink}>
            {copied ? "Link copied" : "Copy link for later"}
          </button>
          <ResumeButton
            onDownload={session.downloadResume}
            className={secondaryButton}
          >
            Download my resume
          </ResumeButton>
        </div>
      </div>

      {session.status === "live" && (
        <div className="flex flex-col gap-2 bg-navy px-6 pb-7 pt-5.5 text-navy-text">
          <div className="flex items-center gap-2.5 text-[15px] font-semibold">
            <span className="size-2.5 rounded-full bg-live"></span>
            {session.visit?.visitorNumber
              ? `You're visitor #${session.visit.visitorNumber.toLocaleString()}`
              : "My backend still saw you"}
          </div>
          <p className="text-[15px] leading-normal text-navy-muted">
            Your visit was logged by a Lambda function and saved as one row in
            DynamoDB, marked as a phone visit. It deletes itself after 30 days.
          </p>
          <button
            type="button"
            onClick={deleteVisit}
            disabled={deleteState === "deleting"}
            className="min-h-11 cursor-pointer self-start text-[15px] font-semibold underline underline-offset-4 disabled:cursor-default disabled:opacity-70"
          >
            {deleteLabels[deleteState]}
          </button>
        </div>
      )}

      {session.status === "deleted" && (
        <div className="bg-navy px-6 pb-7 pt-5.5 text-[15px] leading-normal text-navy-text">
          Deleted. My backend no longer has any record of your visit.
        </div>
      )}
    </div>
  );
}
