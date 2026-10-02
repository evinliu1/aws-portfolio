const skills = [
  "Python",
  "AWS Lambda",
  "DynamoDB",
  "API Gateway",
  "AWS CDK",
  "React",
];

export default function Skills() {
  return (
    <section id="skills">
      <h2>Skills</h2>
      <ul>
        {skills.map((skill) => (
          <li key={skill}>{skill}</li>
        ))}
      </ul>
    </section>
  );
}
