# relay-and-spawn — decisions

## Decided

- Mandate is written automatically when the chain is concrete + ungated; the only question is spawn-now vs leave — a wrong mandate costs one "Drop it" at startup.
- Startup asks before taking a mandate (Take it / Not now / Drop it) — a mandate can sit for days and the person starting may have come for something else.
- Wrap-up saves before offering a relay — an early draft asked first and a stopped run left feature-status.yml uncommitted.
- Spawned agents open in their own Muxy worktree tab, not a split — a split died with the parent's tab and was filed under the parent's worktree.

## Ruled out

- Finding the new Muxy pane by "first new pane" — a never-opened worktree also gets an auto Terminal pane that sorts first; match by tab title + cwd.
- `muxy read-screen` to check a background agent — returns blank until the tab is shown.
