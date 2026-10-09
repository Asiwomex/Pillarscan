/** The logo: the signature in miniature, a pillar with one damaged block. */
export function Mark({ className, sound = "var(--sound)" }: { className?: string; sound?: string }) {
  return (
    <svg viewBox="0 0 16 16" className={className} aria-hidden="true">
      <rect x="0" y="0" width="16" height="3" rx="1" fill={sound} />
      <rect x="3" y="4.5" width="4.5" height="3" rx="0.75" fill={sound} />
      <rect x="8.5" y="4.5" width="4.5" height="3" rx="0.75" fill="var(--high)" />
      <rect x="3" y="8.5" width="10" height="3" rx="0.75" fill={sound} />
      <rect x="0" y="13" width="16" height="3" rx="1" fill={sound} />
    </svg>
  );
}
