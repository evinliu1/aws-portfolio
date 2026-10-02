const skills = [
  "Python",
  "SQL",
  "AWS Lambda",
  "API Gateway",
  "DynamoDB",
  "AWS CDK",
  "pytest",
  "React",
];

export default function Skills() {
  return (
    <section id="skills" className="flex flex-col gap-4">
      <h2 className="font-display text-[34px] font-bold">Skills</h2>
      <ul className="flex flex-wrap gap-2.5">
        {skills.map((skill) => (
          <li key={skill} className="rounded-full bg-chip px-4 py-2">
            {skill}
          </li>
        ))}
      </ul>
    </section>
  );
}
