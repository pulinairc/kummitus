#!/usr/bin/env python3
"""
Script to categorize oraakkeli answers using AI.
Run this once to create a categorized JSON file.
"""
import json
import requests
import time
import os

DATA_FILE = "oraakkeli_data.json"
OUTPUT_FILE = "oraakkeli_categorized.json"

# Categories
CATEGORIES = {
    "yes_no": "Kyllä/Ei vastaukset (joo, ei, ehkä, totta kai, tuskin, jne.)",
    "time": "Aikaan liittyvät vastaukset (milloin, koska - esim. '2 viikkoa', 'huomenna', 'ensi vuonna')",
    "person": "Henkilöön liittyvät vastaukset (kuka, kenelle - esim. 'äidillesi', 'kaverille', nimet)",
    "place": "Paikkaan liittyvät vastaukset (missä, mihin - esim. 'Suomessa', 'kotona', 'ulkomailla')",
    "count": "Lukumäärä vastaukset (montako - esim. '5', '100', 'paljon')",
    "reason": "Syy vastaukset (miksi - esim. 'koska...', 'siksi että...')",
    "what": "Mitä/mikä vastaukset (asiat, esineet, abstraktit käsitteet)",
    "how": "Miten/kuinka vastaukset (tavat, keinot)",
    "other": "Muut vastaukset jotka eivät sovi mihinkään kategoriaan"
}

def call_ai(prompt, max_tokens=2000, retries=3):
    """Call Pollinations API with retry logic"""
    for attempt in range(retries):
        try:
            response = requests.post(
                "https://text.pollinations.ai/openai",
                json={
                    "model": "openai",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens
                },
                headers={"Content-Type": "application/json"},
                timeout=120
            )
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"].strip()
            else:
                print(f"API error: {response.status_code} (attempt {attempt + 1}/{retries})")
                if attempt < retries - 1:
                    time.sleep(5)  # Wait before retry
                    continue
            return None
        except Exception as e:
            print(f"Exception: {e} (attempt {attempt + 1}/{retries})")
            if attempt < retries - 1:
                time.sleep(5)
                continue
            return None
    return None

def categorize_batch(answers, batch_num, total_batches):
    """Categorize a batch of answers using AI"""

    answers_text = "\n".join([f"{i+1}. {a}" for i, a in enumerate(answers)])

    prompt = f"""Kategorisoi nämä oraakkelin vastaukset. Jokainen vastaus kuuluu YHTEEN kategoriaan.

KATEGORIAT:
- yes_no: Kyllä/Ei vastaukset (joo, ei, ehkä, totta kai, tuskin, ehdottomasti, luultavasti)
- time: Aikavastaukset (2 viikkoa, huomenna, 10 min, ensi vuonna, pian, ikuisesti)
- person: Henkilövastaukset (äidillesi, kaverille, Mikko, rakastajattarelle, sinulle)
- place: Paikkavastaukset (Suomessa, kotona, ulkona, Afrikassa, täällä)
- count: Lukumäärävastaukset (5, 100, monta, vähän, paljon)
- reason: Syyvastaukset (koska..., siksi että..., sen takia)
- what: Mitä-vastaukset (asiat, esineet, ruuat, abstraktit)
- how: Miten-vastaukset (nopeasti, hitaasti, varovasti, kovaa)
- other: Ei sovi mihinkään yllä olevaan

VASTAUKSET:
{answers_text}

Vastaa VAIN JSON-muodossa näin (ei muuta tekstiä):
{{"1": "yes_no", "2": "time", "3": "person", ...}}

Käytä vastauksen numeroa avaimena ja kategoriaa arvona."""

    result = call_ai(prompt)
    if not result:
        return None

    # Parse JSON from response
    try:
        # Find JSON in response
        start = result.find('{')
        end = result.rfind('}') + 1
        if start >= 0 and end > start:
            json_str = result[start:end]
            return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Response was: {result[:500]}")

    return None

def main():
    # Load answers
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    answers = data.get('answers', [])
    print(f"Loaded {len(answers)} answers")

    # Initialize categorized structure
    categorized = {cat: [] for cat in CATEGORIES.keys()}

    # Process in batches of 50
    batch_size = 50
    total_batches = (len(answers) + batch_size - 1) // batch_size

    # Track progress
    processed = 0
    failed = []

    # Check for existing progress
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            existing = json.load(f)
            categorized = existing.get('categorized', categorized)
            processed = sum(len(v) for v in categorized.values())
            print(f"Resuming from {processed} already categorized answers")

    # Get already categorized answers to skip them
    already_done = set()
    for cat_answers in categorized.values():
        already_done.update(cat_answers)

    # Filter out already done
    remaining = [a for a in answers if a not in already_done]
    print(f"Remaining to categorize: {len(remaining)}")

    total_batches = (len(remaining) + batch_size - 1) // batch_size

    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, len(remaining))
        batch = remaining[start_idx:end_idx]

        print(f"Processing batch {batch_idx + 1}/{total_batches} ({len(batch)} answers)...")

        result = categorize_batch(batch, batch_idx + 1, total_batches)

        if result:
            for idx_str, category in result.items():
                try:
                    idx = int(idx_str) - 1
                    if 0 <= idx < len(batch):
                        answer = batch[idx]
                        if category in categorized:
                            categorized[category].append(answer)
                        else:
                            categorized['other'].append(answer)
                except (ValueError, IndexError):
                    pass

            # Save progress after each batch
            output_data = {
                "categorized": categorized,
                "stats": {cat: len(items) for cat, items in categorized.items()}
            }
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            current_total = sum(len(v) for v in categorized.values())
            print(f"  Saved progress: {current_total} answers categorized")
        else:
            print(f"  Batch failed, adding to retry list")
            failed.extend(batch)

        # Rate limiting
        time.sleep(2)

    # Final stats
    print("\n=== FINAL STATS ===")
    for cat, items in categorized.items():
        print(f"{cat}: {len(items)} answers")

    total = sum(len(v) for v in categorized.values())
    print(f"\nTotal categorized: {total}/{len(answers)}")

    if failed:
        print(f"Failed to categorize: {len(failed)} answers")

if __name__ == "__main__":
    main()
