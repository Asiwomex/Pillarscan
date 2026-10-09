import { ImageResponse } from "next/og";

// The picture shown when the site's link is shared. Drawn from the same
// block pillars as the hero, so the preview looks like the page.
export const alt = "Pillarscan: find the cracks in your AWS account";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const NIGHT = "#0a1420";
const SOUND = "#2dd4bf";
const HIGH = "#ef6820";
const MEDIUM = "#eaaa08";
const LOW = "#8fa3bf";

// Each pillar from the top row down: failures first, sound blocks at the base.
const PILLARS = [
  [HIGH, HIGH, HIGH, MEDIUM, MEDIUM, SOUND, SOUND, SOUND, SOUND, SOUND, SOUND, SOUND],
  [MEDIUM, MEDIUM, LOW, LOW, SOUND, SOUND, SOUND, SOUND],
  [MEDIUM, LOW, LOW, LOW, LOW, SOUND, SOUND, SOUND, SOUND, SOUND],
];

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: 80,
          background: NIGHT,
          color: "#eef2f8",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", width: 640 }}>
          <div style={{ fontSize: 34, color: SOUND, fontWeight: 600 }}>Pillarscan</div>
          <div
            style={{
              marginTop: 24,
              fontSize: 76,
              fontWeight: 600,
              lineHeight: 1.04,
              letterSpacing: -2,
            }}
          >
            Find the cracks in your AWS account.
          </div>
          <div style={{ marginTop: 28, fontSize: 30, color: "#9aa9bf" }}>
            A read-only posture review across security, reliability and cost.
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "flex-end", gap: 28 }}>
          {PILLARS.map((blocks, pillar) => (
            <div
              key={pillar}
              style={{ display: "flex", flexWrap: "wrap", width: 100, gap: 8 }}
            >
              {blocks.map((color, index) => (
                <div
                  key={index}
                  style={{ width: 46, height: 46, borderRadius: 6, background: color }}
                />
              ))}
            </div>
          ))}
        </div>
      </div>
    ),
    size,
  );
}
