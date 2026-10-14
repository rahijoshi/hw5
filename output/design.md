# Design — the Campus Customs ops desk

The brief for this problem was to make something people would actually want to sit at, not just a
CRUD table with a "run" button. The organizing idea: **a literal desk**. A real ops desk has an
inbox tray of things to handle, a blotter in the middle where you actually work one thing at a
time, a cash drawer you can glance at, and paper slips that need an actual signature before money
moves. Every layout and interaction choice below comes back to that metaphor.

## Palette: lavender and yellow, on purpose

The course convention (`AGENTS.md`) sets lavender-and-yellow-flowers as the default app style, and
it turned out to fit the desk metaphor well rather than fighting it: lavender reads as a calm,
slightly unusual "desk felt" background instead of the generic white-and-blue every admin
dashboard defaults to, and yellow is exactly the color a real desk already uses for
attention — sticky notes, highlighter, a "sign here" flag. So yellow isn't decorative here; it's
load-bearing. It marks exactly one thing: **something needs a human**. The "Needs approval" ticket
badge is yellow. The approval slip is yellow. The cash widget flashes yellow for a second when the
balance changes. Nothing else on the page is yellow, so the color itself is the alert system — you
can tell at a glance, before reading a word, whether anything is waiting on you.

The small flower glyph (`✿`) in the header ties back to the course's own visual convention and to
`output/desk_tickets.html` from Problem 6, so the homework's own artifacts read as one consistent
world rather than three unrelated screens.

## Layout: a board and a desk, not a table

Left column — **the board**: three ticket cards, always visible, each just a subject line,
requester, type, and a status pill. This is deliberately thin. It's an inbox, not a spreadsheet —
you shouldn't need to read ten fields to decide which ticket to open next.

Right column — **the desk**: whichever ticket is selected gets the big surface. Facts (sku, size,
qty, lease_id, invoice_id — only the ones that actually exist for that ticket, so a rent ticket
doesn't show four empty "sku: —" boxes), the original requester's note in italics like a sticky
note stuck to the file, a Start/Re-run button, and then the live feed.

This two-pane split is the one structural choice everything else hangs off: you're never
managing the whole board and reading one ticket's blow-by-blow activity in the same glance — you
pick one thing to actually work, the way a person sitting at a real desk would.

## How agents read differently from each other

Five agents delegating to each other is only useful to watch if you can tell who's talking without
reading every line. Each agent gets one fixed color used everywhere it appears — the feed, the
summary cards, the little badge — chosen to mean something instead of being an arbitrary rainbow:

- **Boss** — deep plum/indigo. The one making calls, so the most "executive" color on the board.
- **Inventory** — teal/green. Stock, shelves, physical goods.
- **Accounting** — amber/gold. Money — the one color family that visually rhymes with the yellow
  approval system, which is intentional: Accounting is the agent whose work eventually produces
  something that needs that yellow signature.
- **Facilities** — slate blue. Buildings, leases, the physical shop space.
- **Customer Service** — rose/pink. The one agent actually speaking to a person, given the
  warmest color of the five.
- **Human approval** — a sixth color, green, used only for the entry the backend itself appends
  once a human actually signs something. It's visually distinct from all five agents on purpose —
  it's the one line in the whole feed that isn't an AI talking.

In the feed, a tool call and a plain final answer are typeset differently (`tool_name()` in a
monospace chip with its real arguments underneath, versus a line of plain prose for a final
answer) so you can tell "the agent did something" from "the agent is now telling you what it
thinks" without parsing sentence structure.

## Watching it happen, not just the result

The feed polls every two seconds and auto-scrolls as new lines land, with a small fade-in on each
new line — rejected an instant "jump to the final answer" approach specifically because the brief
asked to *watch agents work*, not just read a summary afterward. A pulsing dot on the ticket card
and the "Start" button itself (which turns into "Agents working…" with the same pulse) is the only
other "it's alive" signal — deliberately restrained, no spinners or progress bars pretending to
know how long a multi-agent delegation chain will take, since it genuinely varies.

Once a run leaves `open`, the live feed freezes and a **per-agent summary grid** appears below it —
one card per agent that actually touched the ticket, bordered in that agent's color, showing which
tools it called and its own final sentence or two. This is the "what did everyone actually do"
answer the brief asked for, built directly from the same audit trail (each agent's own
`stop_reason: "completed"` entry), not a separately-written summary — so it can never say something
the agent didn't actually say.

## The signature slip — approving a payment

This is the one interaction designed to feel different from the rest of the app on purpose. A
pending payment renders as a dashed-border yellow slip with a vertical "signature needed" stamp
down the left edge — visually closer to a real paper requisition than a software dialog. Clicking
"Review & approve" doesn't pop a modal (modals interrupt; this is meant to feel like picking up a
pen, not getting interrupted) — it opens an inline name field set in an italic serif font, the one
deliberate typographic break from the sans-serif interface everywhere else, specifically to read
as *handwriting* rather than a form field. Typing a name and clicking "Sign & approve" is the only
path in the entire app that can move money — exactly mirroring the real backend rule that
`make_payment` cannot execute without a human in the loop.

## Resolved tickets and the cash drawer

A resolved ticket's status pill turns green and that's the only change — no confetti, no
animation, because the thing a real ops desk wants from "resolved" is *quiet*, not celebration.
The checking balance sits in its own small card in the header, pinned where it's visible no matter
which ticket is open, because cash is shop-wide state, not something that belongs to whichever
ticket you happen to be looking at. When an approval actually changes it, the card briefly gets a
yellow glow and scales up a touch for about a second — small enough not to be gimmicky, obvious
enough that you don't have to stare at the number to notice the balance just moved.
