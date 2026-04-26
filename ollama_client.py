"""
Ollama client pointing at Phosphor (llama3.1:8b).
LLM handles: parameter interpretation, daily summaries, strategy adjustment suggestions.
LLM does NOT handle: math, position sizing, stop calculations, or execution decisions.
"""

import requests
import json
import config


def ask(prompt, system=None):
    """Send a prompt, return response text."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    resp = requests.post(
        f"{config.OLLAMA_HOST}/api/chat",
        json={"model": config.OLLAMA_MODEL, "messages": messages, "stream": False},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def summarize_positions(positions, account):
    """Ask LLM to produce a plain-English daily summary."""
    system = (
        "You are a trading assistant. Summarize portfolio state clearly and briefly. "
        "Do not suggest trades or override existing rules."
    )
    pos_text = "\n".join(
        f"{p.symbol}: {p.qty} shares @ avg ${float(p.avg_entry_price):.2f}, "
        f"current ${float(p.current_price):.2f}, P&L ${float(p.unrealized_pl):.2f}"
        for p in positions
    )
    prompt = (
        f"Account equity: ${float(account.equity):.2f}\n"
        f"Cash: ${float(account.cash):.2f}\n\n"
        f"Positions:\n{pos_text}\n\n"
        "Provide a brief daily summary."
    )
    return ask(prompt, system=system)


def suggest_parameter_adjustment(symbol, recent_performance):
    """LLM suggests parameter tweaks — human reviews before applying."""
    system = (
        "You are a trading assistant. Suggest parameter adjustments based on performance. "
        "Output JSON only: {\"trailing_stop_pct\": float, \"raise_trigger_pct\": float, \"reason\": str}"
    )
    prompt = (
        f"Symbol: {symbol}\n"
        f"Recent performance: {recent_performance}\n"
        "Suggest parameter adjustments."
    )
    raw = ask(prompt, system=system)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None
