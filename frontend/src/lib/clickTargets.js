// Elements whose clicks are counted. Mark one with data-track="<id>" to track it.
// The backend only accepts these ids: keep backend/src/events/handler.py CLICK_TARGETS in sync.

export const SKILLS = [
  "Python",
  "SQL",
  "AWS Lambda",
  "API Gateway",
  "DynamoDB",
  "AWS CDK",
  "pytest",
  "React",
];

export function skillTarget(skill) {
  return `skill-${skill.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
}

export const CLICK_LABELS = {
  "download-resume": "Download resume",
  "get-in-touch": "Get in touch",
  ...Object.fromEntries(SKILLS.map((skill) => [skillTarget(skill), skill])),
};
