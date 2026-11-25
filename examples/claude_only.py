"""effitrap with Claude only. You never switch models by hand.

    pip install anthropic effitrap.zip
    export ANTHROPIC_API_KEY=...
    python examples/claude_only.py

Urgent question  -> ask():       smallest Claude that's good enough, answered now.
Can wait         -> ask_later(): knapsack right-sizes every question, waits for the
                                 cleanest hour, then sends ONE Message Batch
                                 (Anthropic charges 50% less for batches).
"""
import time

from effitrap import CLAUDE_FAMILY, Gate
from effitrap.cli import best_start

gate = Gate(budget_wh=5000, models=CLAUDE_FAMILY, ledger_file=".effitrap-budget.json")


def ask(client, prompt):
    choice = gate.pick(prompt)                      # Haiku, Sonnet or Opus: effitrap decides
    if choice.model is None:
        return None                                 # this week's energy budget is used up
    msg = client.messages.create(model=choice.model, max_tokens=1024,
                                 messages=[{"role": "user", "content": prompt}])
    return msg.content[0].text


def ask_later(client, prompts, forecast=None, slot_hours=0.5, sleep=time.sleep):
    choices = gate.pick_many(prompts)               # exact knapsack over the whole group
    requests = [{"custom_id": f"q{i}",
                 "params": {"model": c.model, "max_tokens": 1024,
                            "messages": [{"role": "user", "content": p}]}}
                for i, (p, c) in enumerate(zip(prompts, choices)) if c.model]
    if forecast:                                    # e.g. effitrap.carbon.fetch_gb_forecast()
        sleep(best_start(forecast, 1) * slot_hours * 3600)   # wait for the cleanest half hour
    return client.messages.batches.create(requests=requests)


if __name__ == "__main__":
    import anthropic
    from effitrap.carbon import fetch_gb_forecast
    client = anthropic.Anthropic()
    print(ask(client, "Translate 'good morning' into Hindi"))          # -> Haiku
    batch = ask_later(client, ["Summarise this week's meeting notes: ...",
                               "Prove this theorem about prime numbers"],
                      forecast=fetch_gb_forecast(24))
    print("Batch sent:", batch.id)
