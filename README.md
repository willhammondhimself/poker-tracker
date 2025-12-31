# Quant Poker Edge

A professional-grade poker analytics platform built with **Streamlit**, featuring Monte Carlo simulation, behavioral finance analysis, and AI-powered coaching.

---

## Features

### Core Analytics
- **Session Tracking** - Log live sessions or completed games with buy-in/cash-out
- **Hand Logger** - Record hands with smart card selector (2-click, keyboard shortcuts)
- **LeakFinder** - Identify negative EV spots and generate prioritized improvement recommendations
- **My Edge Dashboard** - Top exploits, leaks, and overall BB/100 metrics

### Quant Portfolio Modules

#### Monte Carlo Bankroll Simulator
*Risk of Ruin analysis using probability modeling*
- Simulates 1000+ bankroll trajectories using `np.random.normal()`
- Calculates: Risk of Ruin %, Expected Value, 5th/95th percentiles
- Interactive Plotly fan chart with confidence bands
- Kelly Criterion calculator for optimal bankroll sizing

#### Tilt Detection Engine
*Behavioral finance analysis for emotional control*
- Detects downswings (>10bb loss in 50-hand windows)
- Monitors VPIP increase after losses (loss-chasing behavior)
- Aggression spike detection
- 0-10 Tilt Score with color-coded alerts

#### Automated Opponent Tagging
*Statistical classification engine*
- Auto-tags opponents based on VPIP/PFR/AF thresholds
- Classifications: Whale, Nit, LAG, TAG, Maniac, Calling Station, etc.
- Generates exploitation tips per player type

#### Interactive Hand Replayer
*Street-by-street hand visualization*
- Casino-style green felt table display
- Step through Preflop → Flop → Turn → River → Showdown
- Hero cards, board, and opponent placeholders

### GTO Analytics

#### Quant Radar
*Vector distance analysis vs GTO baseline*
- Scatterpolar visualization comparing Hero stats to optimal play
- Metrics: VPIP, PFR, 3-Bet, Aggression Factor, WTSD
- Color-coded deviation indicators with stat breakdown table

### Institutional Reporting

#### Fund Tearsheet
*Automated PDF generation for stakeholder reporting*
- Professional performance report with executive summary
- Key metrics: Total P/L, hourly rate, session win rate
- Playstyle analysis vs GTO baseline
- Session history table with trailing 15 sessions

### Risk Tools

#### Luck Bucket
*EV variance analysis for all-in spots*
- Pre-loaded equity table (AA vs KK = 82%, etc.)
- Real-time EV calculation with pot odds
- Luck factor tracking: Actual vs Expected outcomes

### AI Coach Integration
- Perplexity API integration for GTO analysis
- Hand rating (1-10) with detailed breakdown
- Alternative line suggestions
- Opponent profile awareness

### Data Import
- **Ignition Casino** hand history parser
- Automatic session reconstruction from Zone Poker exports

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Streamlit |
| Visualization | Plotly |
| Data | Pandas, NumPy |
| Simulation | NumPy (Monte Carlo) |
| Reporting | fpdf2 |
| AI | Perplexity API |
| Storage | JSON files |

---

## Installation

```bash
# Clone repository
git clone https://github.com/yourusername/poker-tracker.git
cd poker-tracker

# Install dependencies
pip install -r requirements.txt

# Run application
streamlit run app.py
```

---

## Configuration

### AI Coach (Optional)
Create `.streamlit/secrets.toml`:
```toml
[perplexity]
api_key = "pplx-your-api-key"
```

Or enter your API key in the sidebar settings.

---

## Project Structure

```
poker-tracker/
├── app.py                    # Main Streamlit application
├── requirements.txt          # Python dependencies
├── components/
│   ├── analytics.py          # Charts and metrics
│   ├── card_selector.py      # Smart card picker
│   ├── ev_calculator.py      # Luck Bucket EV analysis
│   ├── hand_visualizer.py    # Casino-quality card rendering
│   ├── hand_replayer.py      # Interactive hand replay
│   ├── radar_chart.py        # Quant Radar visualization
│   └── session_form.py       # Session logging forms
├── utils/
│   ├── ai_coach.py           # Perplexity API integration
│   ├── analytics_engine.py   # LeakFinder algorithms
│   ├── data_loader.py        # JSON persistence
│   ├── ignition_parser.py    # Hand history parser
│   ├── monte_carlo.py        # Bankroll simulation
│   ├── poker_math.py         # Confidence intervals
│   ├── range_analyzer.py     # Range visualization
│   ├── report_generator.py   # PDF tearsheet generation
│   ├── tagging_engine.py     # Opponent classification
│   └── tilt_detector.py      # Behavioral analysis
└── data/
    ├── sessions.json
    ├── hands.json
    ├── opponents.json
    └── settings.json
```

---

## Screenshots

*Dashboard with My Edge card, Confidence Intervals, and Tilt Score*

*Monte Carlo Simulator with fan chart and Risk of Ruin*

*Hand Replayer with street-by-street reveal*

---

## License

MIT

---

## Author

Built for trading interview demonstrations showcasing:
- Probability modeling (Monte Carlo)
- Statistical analysis (Confidence Intervals)
- Behavioral finance (Tilt Detection)
- Data engineering (Parsers, JSON persistence)
- Full-stack development (Streamlit, Plotly)
