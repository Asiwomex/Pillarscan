# Pillarscan - Design

> A building inspector's report for a cloud account: sound structure is one calm colour, and damage is the only thing that shouts.

**Subject / audience / job:** An AWS posture review dashboard. Recruiters and hiring engineers land here; they know what a cloud console looks like and give it about ten seconds. The one job: see at a glance how healthy the account is, then open a finding and read what is wrong and how to fix it.

**Theme:** a dark site around a light product. The marketing sections are dark navy; the live demo sits in them as a light window, so it reads as the product itself.

The demo should feel like a real security product you could use all day: flat white panels on a cool grey page, one typeface, tight and even spacing. The site around it is dark and confident, with one large headline. Personality comes from one place, the pillars built out of blocks. Everything else stays quiet so the severity colours carry the meaning.

## The signature

**Pillars built from checks.** Each pillar (Security, Reliability, Cost) is drawn as a stack of small square blocks, one block per finding. A passing check is a solid teal block. A failing one is coloured by severity. A healthy pillar is a solid teal wall; a weak one has warm gaps in it. Every block is clickable and opens that finding.

In the hero the same idea is shown at full size: three stacks of blocks built from the ground up, sound checks at the base and failures on top, where the cracks show.

The same severity colours are then used everywhere else (score bar, chart, table) and for nothing else.

## Color

| Name | Value | Role |
| --- | --- | --- |
| Page | `#F5F7FA` | Page background |
| Surface | `#FFFFFF` | Panels, table, detail sheet |
| Ink | `#0F1B2D` | Text, primary buttons |
| Muted | `#5B6B80` | Secondary text |
| Line | `#DFE4EC` | Borders and dividers |
| Sound (brand) | `#0F766E` | Passing checks, links, focus, the wordmark |
| Critical | `#D92D20` | Severity only |
| High | `#EF6820` | Severity only |
| Medium | `#EAAA08` | Severity only |
| Low | `#8FA3BF` | Severity only |
| Night | `#0A1420` | Site background outside the demo |
| Night raised | `#101D2D` | Cards on the dark site |
| Night line | `#213044` | Borders on the dark site |
| On night | `#EEF2F8` / `#9AA9BF` | Text and muted text on dark |
| Sound bright | `#2DD4BF` | Brand colour on dark: passing blocks, primary button |

Neutrals are tinted towards navy, never flat grey. No gradients.

## Type

- One family: **Instrument Sans** (400, 500, 600), for everything.
- **JetBrains Mono** (400) only for machine identifiers: ARNs, resource IDs, check IDs, regions.
- Base 14px for the app, 13px in the table. Score 48px / 1.0 / -0.03em, weight 600, with its verdict in words beside it. Section titles 15px / 600. Labels are sentence case, 13px, muted. No all-caps tracked labels.
- Numbers use tabular figures.

## Spacing and shape

- Base unit 4px. Panel padding 20px, gap between panels 16px, page gutter 24px (16px on phones).
- Radius: panels 10px, controls 6px, blocks 3px, badges full.
- Panels have a 1px Line border and no shadow. The detail sheet has the only shadow.

## Layout

A menu bar stays fixed to the top of the window on every screen size, with jump links that highlight the current section; on phones the links fold into a menu button. The page, top to bottom: hero (headline left, block pillars right), the live demo, how it works (three plain steps beside real scanner output), the list of checks by pillar, project status, footer (credits: built by Asiwome Boateng, powered by LytaWorks). The demo starts just below the fold line so its top edge is visible on arrival.

Hero headline: clamp(40px, 6.2vw, 72px) / 1.02 / -0.03em, weight 600. Section headings: clamp(28px, 3.4vw, 40px).

Inside the demo, three bands answer three questions in order: how bad is it, where is it, what exactly.

```
[ Pillarscan ]                    [ Demo account | Real account ]  Source
------------------------------------------------------------------------
| 54 /100  Needs attention      | Failed checks by service             |
| 38 of 75 checks failed        | IAM   ######                          |
| [crit|high|medium|low bar]    | EC2   ####                            |
------------------------------------------------------------------------
| Security  58      | Reliability  50     | Cost  42                    |
| ▪▪▪▪▪▪▪▪▪▪        | ▪▪▪▪▪▪▪▪▪▪          | ▪▪▪▪▪▪▪▪▪▪                  |
------------------------------------------------------------------------
| Findings   [Failed 38][Passed 37][All 75]   pillar v  severity v  🔍 |
| severity | finding + resource | service | region | status            |
```

Left aligned throughout. Phones get their own layout, not a squeezed one: full-width 48px buttons, the pillars under the headline, stacked bands, and a table reduced to severity, finding and status. Tap targets are at least 44px.

## Imagery

None. The product is the image.

## Motion

One moment, used twice: blocks appear in a quick staggered sweep. In the hero the pillars build from the ground up on load; in the demo the blocks sweep in when a scan loads or is switched. Easing `cubic-bezier(0.2, 0, 0, 1)`, 240ms per block, 6ms stagger. The detail sheet slides in at 200ms. Nothing else moves. Reduced motion removes the sweep.

## Do

- Use severity colours only for severity.
- Pair every colour with a word or a shape, so nothing depends on colour alone.
- Keep one border style, one radius per element type, one spacing scale.

## Don't

- No serif headlines, cream paper, drafting grids or hairline-rule newspaper layout (the first version).
- No gradients, gradient text, glass, glow or starfields.
- No invented proof: no testimonials, logos, pricing or sign-up for things that do not exist. The status section says plainly what is built and what is planned.
- No decorative monospace, no all-caps tracked labels.
- Nothing borrowed from Refraxion's branding or layout.
- None of the patterns the owner flagged as looking machine-made: pill badges above headlines, status dots, icons in rounded squares above headings, three identical feature cards, numbered 01/02/03 labels, cards nested inside cards, coloured stripes down card edges, a giant statistic with a tiny label, frosted glass, glows, gradient text, purple-to-blue gradients, Inter, beige with an italic serif, em dashes, and filler copy such as "supercharge your workflow".
