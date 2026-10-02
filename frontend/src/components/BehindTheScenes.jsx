const sampleEvents = [
  {
    time: "1:38",
    text: "You clicked a skill. The click went through API Gateway to Lambda in 21 ms.",
  },
  {
    time: "0:51",
    text: "You scrolled to About. Section views are stored so I can see what people actually read.",
  },
  {
    time: "0:15",
    text: "First heartbeat. Your session row in DynamoDB was updated.",
  },
  {
    time: "0:00",
    text: "You arrived. A Lambda function woke up from a cold start in 412 ms and logged your visit.",
  },
];

const requestPath = ["CloudFront", "API Gateway", "Lambda", "DynamoDB"];

function Stat({ value, label }) {
  return (
    <div className="rounded-xl bg-white/7 p-5">
      <div className="font-display text-[40px] font-medium leading-tight">
        {value}
      </div>
      <div className="text-[15px] text-navy-muted">{label}</div>
    </div>
  );
}

export default function BehindTheScenes() {
  return (
    <aside
      aria-label="What my backend sees"
      className="sticky top-0 flex h-screen flex-col gap-10 self-start overflow-y-auto bg-navy px-12 pb-12 pt-18 text-navy-text"
    >
      <div>
        <h2 className="font-display text-[28px] font-bold">
          What my backend sees
        </h2>
        <p className="text-navy-muted">Updating as you scroll and click</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Stat value="1:42" label="time on page" />
        <Stat value="Georgia" label="from CloudFront headers" />
      </div>

      <ol>
        {sampleEvents.map((event, index) => (
          <li
            key={event.time}
            className="flex gap-4 border-b border-white/12 py-4 leading-normal"
          >
            <span
              className={`w-14 shrink-0 text-[15px] ${
                index === 0 ? "text-live" : "text-navy-muted"
              }`}
            >
              {event.time}
            </span>
            <p>{event.text}</p>
          </li>
        ))}
      </ol>

      <div className="mt-auto flex flex-col gap-3">
        <p className="text-navy-muted">The path every request takes</p>
        <ul className="flex flex-wrap gap-2">
          {requestPath.map((service) => (
            <li
              key={service}
              className="rounded-full border border-white/30 px-3 py-1.5 text-[15px]"
            >
              {service}
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
