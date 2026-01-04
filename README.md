# AI Poker Coach

Session tracker with AI analysis I built for my Ignition grind. Wanted something that does bankroll math properly and finds leaks automatically instead of a spreadsheet.

## What it does

- **Session logging** - Track live sessions or log completed ones
- **Hand logger** - Record hands with a card picker (keyboard shortcuts work)
- **LeakFinder** - Finds your -EV spots and ranks them
- **My Edge** - Shows your top exploits and overall BB/100

## The quant stuff

### Monte Carlo bankroll sim
Runs 1000 trajectories to estimate risk of ruin. Has a Kelly calculator too. The fan chart looks cool but honestly you probably already know if you're rolled for the stakes.

### Tilt detection
Looks for downswings (>10bb in 50 hands) and whether you start spewinig after. Gives you a 0-10 score. Mostly useful for post-session review.

### Opponent tagging
Auto-tags villains based on VPIP/PFR/AF. Categories are the usual - whale, nit, LAG, etc. Suggests exploits but they're pretty obvious (don't bluff the calling station, etc).

### Hand replayer
Step through hands street by street. Green felt table, looks nice.

### GTO Radar
Scatterpolar comparing your stats to a baseline. Shows where you're deviating.

### PDF tearsheet
Generates a report you could theoretically show a backer. Has your hourly, session winrate, trailing 15 sessions.

### Luck bucket
EV calculator for all-in spots. Tracks how much you've run above/below EV.

## Quant Lab (the fun stuff)

### Volatility (GARCH)
GARCH(1,1) on session PnL. Flags if variance is abnormally high/low compared to your history. Useful for knowing when to take shots or move down.

### Opponent clustering
PCA + K-means on villain stats. Groups regs into archetypes (nit, lag, etc). Needs ~50 opponents with decent sample to be useful.

### Winrate confidence intervals
Bootstrap resampling (10k iterations) to get 95% CI on your actual winrate. Shows P(you're a winner) which is humbling with small samples.

## Caveats

- Need 50+ opponents for clustering to mean anything
- GARCH needs 10+ sessions minimum
- Winrate CI is wide until you have 10k+ hands
- Only parses Ignition Zone format right now

## Setup

```bash
git clone https://github.com/yourusername/poker-tracker.git
cd poker-tracker
pip install -r requirements.txt
streamlit run app.py
```

### AI Coach (optional)
Add your Perplexity API key to `.streamlit/secrets.toml`:
```toml
[perplexity]
api_key = "pplx-your-key"
```

## Structure

```
poker-tracker/
├── app.py              # main streamlit app
├── analytics/          # GARCH, clustering, bayesian stuff
├── components/         # UI components
├── utils/              # parsers, calculators, data loading
└── data/               # JSON storage
```

---

Built to track sessions and practice scipy/sklearn. The quant stuff is mostly for fun - you don't need GARCH to know you're running bad.
