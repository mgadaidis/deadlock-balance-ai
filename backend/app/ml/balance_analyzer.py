"""
Personalised balance analyser.

Verdict layers:
  1. Win-rate threshold (transparent baseline).
  2. IsolationForest anomaly score over (win_rate, pick_rate, kda, avg_damage).

Recommendations are NOT templated. Each one is generated from the specific
metric profile of the hero — what's out of band, by how much, and what the
plausible mechanical lever is. Three text fields are produced per flag:

  * rationale            – the evidence
  * mechanical_reasoning – which dial likely caused the metric to drift
  * macro_impact         – how the imbalance warps team play
  * recommendation       – the concrete change to ship
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from ..config import settings


def _classify(wr: float) -> str:
    if wr > settings.winrate_high:
        return "overpowered"
    if wr < settings.winrate_low:
        return "underpowered"
    return "balanced"


def _profile(row: pd.Series, baselines: dict) -> dict:
    """
    Return a dict describing which of the hero's metrics deviate notably from
    the global baseline (median across the roster). Each entry holds the
    signed z-score so downstream prose can mention magnitude *and* direction.
    """
    out: dict[str, float] = {}
    for k in ["win_rate", "pick_rate", "kda", "avg_damage", "avg_net_worth", "avg_deaths"]:
        mu = baselines[k]["median"]
        sd = baselines[k]["mad"] or 1.0
        z = (float(row[k]) - mu) / sd
        if abs(z) >= 0.8:                       # only mention notable deviations
            out[k] = z
    return out


def _official_context(row: pd.Series) -> str:
    role = str(row.get("role_text") or "").strip()
    playstyle = str(row.get("playstyle") or "").strip()
    bits = []
    if role:
        bits.append(f"official role: {role}")
    if playstyle:
        bits.append(f"official playstyle: {playstyle}")
    return " · ".join(bits)


def _metric_labels(profile: dict) -> list[str]:
    labels = {
        "win_rate": "win-rate band",
        "pick_rate": "pick-rate demand",
        "kda": "fight conversion / survival",
        "avg_damage": "damage output",
        "avg_net_worth": "economy scaling",
        "avg_deaths": "death pressure",
    }
    ordered = sorted(profile.items(), key=lambda kv: abs(kv[1]), reverse=True)
    return [f"{labels.get(k, k)} {'above' if v > 0 else 'below'} roster median ({v:+.1f}σ)" for k, v in ordered]


def _rationale(row: pd.Series, profile: dict) -> str:
    """Evidence paragraph.

    Written to a *consistent* three-part structure so the evidence reads at a
    comparable length for every hero (overpowered, underpowered, or balanced)
    and always carries an explanation of what the numbers mean and how far the
    interpretation can be trusted. The two branches below are deliberately
    matched in length so a "quiet" balanced hero is not left with a single
    short line while an outlier gets a paragraph.
    """
    verdict = str(row.get("verdict", ""))
    verdict_hint = {
        "overpowered": "above the healthy win-rate band",
        "underpowered": "below the healthy win-rate band",
        "balanced": "inside the healthy win-rate band",
    }.get(verdict, "relative to the healthy win-rate band")

    # 1) Observed profile — identical structure for every hero.
    profile_line = (
        f"Observed profile across {int(row['matches']):,} qualifying matches: "
        f"win rate {row['win_rate']:.1%} ({verdict_hint}), pick rate {row['pick_rate']:.1%}, "
        f"KDA {row['kda']:.2f}, average damage {row['avg_damage']:.0f}, "
        f"net worth {row['avg_net_worth']:.0f}, deaths {row['avg_deaths']:.1f}."
    )

    # 2) Deviation analysis — both branches are sized similarly so the evidence
    #    never collapses to one short sentence for heroes near the median.
    if profile:
        metric_text = "; ".join(_metric_labels(profile)[:3])
        signal_line = (
            f"Secondary signals standing out against the roster median: {metric_text}. "
            "These are the metrics most likely to explain why the win rate landed where it did, "
            "and they are where any investigation should start."
        )
    else:
        signal_line = (
            "No secondary metric sits far from the roster median: fight conversion, damage output, "
            "economy scaling and death pressure all track the typical hero, so the win-rate position "
            "is not being driven by a single loud outlier and is best treated as low-intensity monitoring."
        )

    # 3) Methodology / confidence — uniform across every hero.
    method_line = (
        "This read is built from aggregate match analytics and robust median/MAD baselines rather than "
        "per-ability or replay telemetry, so it locates where the hero deviates instead of naming one "
        "guilty ability."
    )
    return " ".join([profile_line, signal_line, method_line])


def _mechanical_reasoning(verdict: str, profile: dict, row: pd.Series) -> str:
    """
    Translate aggregate metrics into a mechanic-level hypothesis. We vary the
    explanation by the loudest signals and avoid naming abilities unless the
    dataset actually contains ability telemetry.
    """
    if verdict == "balanced":
        if profile:
            return (
                "The hero has one or two noticeable metric movements, but they do not combine into a balance-risk pattern. "
                "The safer interpretation is role expression rather than overtune: the hero may be good at one job while paying for it elsewhere."
            )
        return "Metrics sit inside the roster's healthy band; KDA, damage, economy, and deaths do not show a reliable balance-risk pattern."

    ordered = sorted(profile.items(), key=lambda kv: abs(kv[1]), reverse=True)
    keys = {k for k, _ in ordered}
    loudest = ordered[0] if ordered else (None, 0.0)
    key, z = loudest

    if verdict == "overpowered":
        if {"avg_damage", "avg_net_worth"}.issubset(keys):
            return (
                "The problem looks like a scaling curve rather than a single isolated stat: damage and economy both rise together, "
                "which usually means the hero reaches item timings too safely or converts souls into fight impact too efficiently. "
                "Investigate farming tempo, damage scaling, and item interactions before touching base durability."
            )
        if key == "avg_damage" and z > 0:
            return (
                f"Damage is the loudest signal ({z:+.1f}σ). That points toward damage scaling, cooldown uptime, or item-amplified burst as the likely pressure source. "
                "This is not enough to name a specific overpowered ability; ability damage/cast data would be required for that."
            )
        if key == "kda" and z > 0:
            return (
                f"KDA is unusually high ({z:+.1f}σ), so the hero is either surviving failed engages, finishing fights too consistently, or both. "
                "The first review target should be survivability/escape/engage reliability, not a blind damage reduction."
            )
        if key == "pick_rate" and z > 0:
            return (
                f"Pick rate is unusually high ({z:+.1f}σ) while win rate remains above band. That combination is more serious than a niche high-win-rate outlier, "
                "because the hero performs even when many players select it. Treat this as broad reliability until item/build data disproves it."
            )
        return (
            "Several signals are above baseline at the same time. The issue is probably not one dramatic outlier but a kit budget that is too forgiving across damage, safety, and economy."
        )

    # underpowered
    if {"avg_damage", "avg_net_worth"}.issubset(keys) and profile.get("avg_damage", 0) < 0 and profile.get("avg_net_worth", 0) < 0:
        return (
            "Damage and economy are both below baseline, which suggests the hero is not reaching meaningful item spikes or does not convert farm into pressure. "
            "A pure survivability buff would not solve this if the core issue is weak scaling/value conversion."
        )
    if key == "avg_deaths" and z > 0:
        return (
            f"Deaths are the loudest negative signal ({z:+.1f}σ above baseline). The hero is being punished before their kit can generate value. "
            "Review base durability, escape reliability, and early-lane vulnerability before increasing damage."
        )
    if key == "avg_damage" and z < 0:
        return (
            f"Damage trails the roster by {abs(z):.1f}σ. The hero appears to participate but fails to convert participation into pressure, "
            "so the likely lever is damage reliability, scaling timing, or ability uptime rather than broad stat buffs."
        )
    if key == "pick_rate" and z < 0:
        return (
            f"Pick rate is low ({z:+.1f}σ) and win rate is also below band. That is a serious adoption signal: even players who choose the hero are not being rewarded. "
            "Investigate usability/friction and build dependence before deciding on raw numbers."
        )
    return (
        "Multiple metrics sit below baseline, suggesting the hero underdelivers on its intended identity rather than suffering from one obvious numerical problem."
    )


def _macro_impact(verdict: str, row: pd.Series, profile: dict) -> str:
    if verdict == "balanced":
        return "Negligible meta impact — hero contributes to comp diversity and should stay under routine monitoring."
    nw = row["avg_net_worth"]
    nw_z = profile.get("avg_net_worth", 0.0)
    pr_z = profile.get("pick_rate", 0.0)
    if verdict == "overpowered":
        if pr_z > 0.8 and nw_z > 0.8:
            return (
                f"High pick demand plus avg net worth {nw:.0f} ({nw_z:+.1f}σ) can warp drafts: teams are incentivized to pick/ban the hero early and play around their power spike."
            )
        if nw_z > 0:
            return (
                f"Avg net worth {nw:.0f} ({nw_z:+.1f}σ) suggests faster scaling into mid game; opponents may be forced into reactive objective defence earlier than intended."
            )
        return "The hero creates pressure even without a clear economy lead, so the macro concern is reliable teamfight impact rather than farming tempo."
    # underpowered
    if nw_z < -0.8:
        return "Low economy conversion makes the draft play from behind: the team reaches item timings later and loses objective tempo around mid-game fights."
    return "Drafting this hero likely reduces teamfight weight or reliability; the team may need to over-invest resources to get normal value from the pick."


def _pct_band(gap: float, z: float) -> tuple[int, int]:
    """Suggested starting magnitude (in percent) for a lever change.

    Derived from how far the win rate sits from the 50% midpoint plus the
    loudest secondary signal, so the number is specific to each hero. A small
    range is returned instead of a single figure so it reads as a starting
    point for testing rather than false precision.
    """
    base = gap * 100.0 * 0.95          # ≈ win-rate points away from the midpoint
    boost = min(abs(z), 3.0) * 0.8     # louder secondary signals widen the change
    change = max(2.0, min(12.0, base + boost))
    low = max(1, round(change - 1.5))
    high = round(change + 1.5)
    return low, high


def _recommendation(verdict: str, profile: dict, row: pd.Series) -> str:
    """
    Concrete, per-hero recommendation. Every recommendation now states the
    hero's current win rate, its signed distance from the 50% midpoint, and a
    suggested percentage band for the change — all computed from this hero's own
    metrics, so the figures differ from hero to hero. The change band is framed
    as a tested starting point because exact tuning still needs ability/item
    telemetry.
    """
    wr = float(row["win_rate"])
    wr_pct = wr * 100.0
    mid_delta = (wr - 0.5) * 100.0     # signed points from the 50% midpoint
    low_line = settings.winrate_low * 100.0
    high_line = settings.winrate_high * 100.0

    if verdict == "balanced":
        to_op = high_line - wr_pct
        to_up = wr_pct - low_line
        margin = min(to_op, to_up)
        return (
            f"Hold — no balance change recommended. Win rate {wr_pct:.1f}% sits {to_op:.1f} points below the "
            f"overpowered line ({high_line:.0f}%) and {to_up:.1f} points above the underpowered line "
            f"({low_line:.0f}%), leaving roughly {margin:.1f} points of margin before any intervention would be "
            "justified. Keep on routine watch in case adjacent item or hero changes push it out of band."
        )

    # win_rate is the verdict metric itself, not a tuning lever, so exclude it
    # when choosing which dial to point the developer at.
    ordered = sorted(
        ((k, v) for k, v in profile.items() if k != "win_rate"),
        key=lambda kv: abs(kv[1]), reverse=True,
    )
    key, z = ordered[0] if ordered else (None, 0.0)
    gap = abs(wr - 0.5)
    low, high = _pct_band(gap, z)
    intensity = "minor" if gap < 0.025 else "moderate" if gap < 0.055 else "major"

    levers = {
        "avg_damage": "the confirmed damage lever (scaling, base damage, or item-amplified burst)",
        "kda": "fight-reliability tools (escape, sustain, cooldown uptime, or engage safety)",
        "pick_rate_high": "the dominant successful build or interaction rather than the whole kit",
        "pick_rate_low": "usability and build-path friction",
        "avg_deaths": "early durability or escape reliability",
        "avg_net_worth": "farming tempo and soul-to-impact conversion",
    }

    if verdict == "overpowered":
        lever_key = "pick_rate_high" if key == "pick_rate" else key
        lever_text = levers.get(lever_key, "the confirmed power source once telemetry isolates it")
        return (
            f"Recommended action: {intensity} targeted nerf. Win rate {wr_pct:.1f}% is {mid_delta:+.1f} points "
            f"from the 50% midpoint, so as a starting point reduce {lever_text} by roughly {low}–{high}%, then "
            "re-measure for one patch before any further cut. Confirm the source with ability/build data rather "
            "than nerfing a named ability from aggregate stats alone."
        )

    # underpowered
    lever_key = "pick_rate_low" if key == "pick_rate" else key
    lever_text = levers.get(lever_key, "the failing mechanic once telemetry isolates it")
    return (
        f"Recommended action: {intensity} targeted buff. Win rate {wr_pct:.1f}% is {mid_delta:+.1f} points "
        f"from the 50% midpoint, so as a starting point improve {lever_text} by roughly {low}–{high}%, then "
        "re-measure for one patch. Prefer a reliability or scaling adjustment over inventing an ability-specific "
        "buff without telemetry."
    )


def analyse_balance(df: pd.DataFrame) -> list[dict]:
    """Returns one flag dict per hero with enough sample size."""
    if df.empty:
        return []
    work = df.copy()
    work = work[work["matches"].fillna(0) >= 50]
    if work.empty:
        return []

    work["verdict"] = work["win_rate"].apply(_classify)

    # Roster baselines (median + MAD = robust against outliers)
    baselines: dict[str, dict] = {}
    for k in ["win_rate", "pick_rate", "kda", "avg_damage", "avg_net_worth", "avg_deaths"]:
        med = float(work[k].median())
        mad = float((work[k] - med).abs().median()) or 0.001
        baselines[k] = {"median": med, "mad": mad}

    # Multivariate anomaly score
    feats = work[["win_rate", "pick_rate", "kda", "avg_damage"]].fillna(0.0).to_numpy(float)
    if len(feats) >= 5:
        scaled = StandardScaler().fit_transform(feats)
        iso = IsolationForest(contamination=0.15, random_state=42)
        iso.fit(scaled)
        raw = -iso.score_samples(scaled)
        work["anomaly"] = (raw - raw.min()) / (np.ptp(raw) or 1.0)
    else:
        work["anomaly"] = 0.0

    midpoint = (settings.winrate_low + settings.winrate_high) / 2
    work["wr_dev"] = (work["win_rate"] - midpoint).abs()
    work["score"] = work["wr_dev"] * 0.7 + work["anomaly"] * 0.3

    flags: list[dict] = []
    for _, row in work.iterrows():
        prof = _profile(row, baselines)
        verdict = row["verdict"]
        flags.append({
            "hero_id": int(row["hero_id"]),
            "verdict": verdict,
            "score": float(row["score"]),
            "rationale": _rationale(row, prof),
            "mechanical_reasoning": _mechanical_reasoning(verdict, prof, row),
            "macro_impact": _macro_impact(verdict, row, prof),
            "recommendation": _recommendation(verdict, prof, row),
        })
    return flags
