# Data format for the ML/simulator layer

The project separates gathered game data from processing code. New data should be added as JSON/CSV-like rows in this folder, then the backend can load it during refresh/simulation.

## 1. `item_upgrade_paths.json`
Used for simulator item exclusivity. Each row has:

```json
{ "category": "weapon", "base": "Rapid Rounds", "upgrades": ["Burst Fire", "Swift Striker"] }
```

Meaning: these items are one upgrade family. If a user selects **Swift Striker**, **Rapid Rounds** and **Burst Fire** are disabled for that hero build. This is why the UI prevents impossible combinations.

## 2. `hero_item_build_stats.schema.json`
Format for future Statlocker/build-data rows. The most important model fields are:

- `hero_name`
- `item_name`
- `item_category`
- `purchase_rate`
- `win_rate`
- `wpa` (win probability added / item impact)
- `avg_buy_time_s`
- `sample_size`
- `rank_filter` / `match_mode`

When real hero-item build rows are available, the simulator can learn compatibility from observed build outcomes instead of relying only on category/archetype heuristics.

## 3. Current ML feature table
The supervised ML model builds one row per hero from refreshed public API data:

```json
{
  "hero_id": 1,
  "matches": 100000,
  "pick_rate": 0.25,
  "avg_kills": 7.1,
  "avg_deaths": 5.8,
  "avg_assists": 10.3,
  "kda": 2.99,
  "avg_damage": 28000,
  "avg_net_worth": 32000,
  "role_marksman": 1,
  "role_mystic": 0,
  "role_brawler": 0,
  "role_support": 0,
  "target_win_rate": 0.531,
  "target_balance_class": "overpowered"
}
```

The regression model predicts `target_win_rate`. The classification model predicts `target_balance_class`: `overpowered`, `balanced`, or `underpowered`.
