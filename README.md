# AlexMyrusTalksSports — NHL Analytics Platform

A fan-made multi-page NHL statistics and research platform styled to match the dark dashboard design used by the NFL tracker.

## Platform

- NHL Stats Tracker — historical season selector, regular-season/playoff filters, separate skater and goalie leaderboards, per-game data mode where supplied by the upstream API, team/position/player filters, player comparisons, team views, statistical facts, content drafts and CSV export.
- Player Profiles — search by player name or NHL player ID, player landing details, season statistics and game logs.
- Team Platform — rankings and a directory for all 32 franchises. Each dedicated team hub shows the current NHL roster, standings position, current and prior season schedule/results, rivalry links, and cached season summaries.
- Head-to-Head — select any two teams to view their latest cached meeting, recent matchup record, results list, and each team's largest win in the recent cached schedule seasons. The page labels this limited coverage and does not claim an all-time record.
- Advanced Lab — skater realtime, scoring-rate, possession, faceoff, power-play, penalty-kill and time-on-ice reports, plus goalie-specific reports.
- Research Lab — player season-to-season comparisons and season leader searches.
- Calendar & Game Centre — date-range schedule, scores and game boxscores.
- News & League Hub — links to original NHL reporting, plus a live scoreboard and current standings.
- Records Explorer — single-season and single-game rankings for the chosen season and phase.
- System Health — checks whether all static pages are published and whether the same-origin NHL data cache is reachable.\n- Predictions & Draft Centre — projects the 82-game standings pace, generates a divisional playoff bracket, makes a transparent baseline Stanley Cup pick, and estimates the non-playoff draft order.

## NHL statistics

The dashboard keeps skater and goalie datasets separate. Skater categories include points, goals, assists, plus/minus, penalty minutes, power-play points, short-handed goals, shots, shooting percentage and games played. Goalie categories include wins, losses, overtime losses, save percentage, goals-against average, shutouts, saves and shots against.

The Advanced Lab exposes report-based statistics such as hits, blocked shots, takeaways, giveaways, possession metrics, scoring rates, faceoffs, special teams and time on ice where those reports return the selected fields.

Season selection spans 1950–51 through the current configured season. Actual coverage depends on the NHL source: older seasons will not contain every modern metric. Missing values remain unavailable rather than being silently converted to zero.

## Data sources and limitations

The site uses endpoints from the NHL Web API (api-web.nhle.com) and NHL Stats REST API (api.nhle.com/stats/rest). These are undocumented public endpoints and can change without notice. The endpoint reference used during development is community-maintained: https://github.com/pseudo-r/Public-NHL-API. It is not an official NHL developer contract.

GitHub Actions fetches NHL Stats REST summaries and NHL Web API standings, scoreboard, schedules, current team rosters and recent boxscores server-side, then publishes same-origin JSON files with the static site. Team schedules for the current and previous seasons support the team hubs and H2H page. This avoids browser CORS failures for the cached datasets. The cache refreshes on pushes and the scheduled workflow. Player biography details are not yet included in the static cache. Individual player game rows are cached for 2024–25 onward; older game logs remain unavailable in this static build and are labelled accordingly.

The Predictions & Draft Centre uses points-per-game pace multiplied by 82 for regular-season projections. Its playoff picks are a transparent baseline based on projected seeds, not a trained probability model. Draft order is an inverse-standings estimate before lottery results and does not model traded or conditional picks.\n\nThe Records Explorer deliberately labels its output as selected-season/single-game rankings. It does not claim to be a complete all-time NHL record book. The platform should only make that claim after a verified historical data warehouse and coverage audit exist.

## Development and deployment

1. Keep the repository's GitHub Pages source set to GitHub Actions.
2. The workflow named "Validate and deploy NHL analytics platform" runs on pushes to main, manually, and daily at 10:17 UTC.
3. The workflow checks every required page and stylesheet, runs node syntax checks on shared/team JavaScript, syntax-checks every inline page script, and validates generated roster and schedule caches.
4. It copies the complete multi-page platform into the Pages artifact and writes build metadata used by System Health.

## Project status

Independent fan-made project. Not affiliated with or endorsed by the NHL.
