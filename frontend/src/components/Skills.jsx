import { SKILLS, skillTarget } from "../lib/clickTargets";

export default function Skills() {
  return (
    <section id="skills" className="flex flex-col gap-4">
      <h2 className="font-display text-[34px] font-bold">Skills</h2>
      <ul className="flex flex-wrap gap-2.5">
        {SKILLS.map((skill) => (
          <li
            key={skill}
            data-track={skillTarget(skill)}
            className="rounded-full bg-chip px-4 py-2"
          >
            {skill}
          </li>
        ))}
      </ul>
    </section>
  );
}
