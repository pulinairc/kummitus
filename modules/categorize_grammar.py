#!/usr/bin/env python3
"""
Script to categorize oraakkeli answers by grammatical case using AI.
Finnish grammar cases must match between question and answer.
"""
import json
import requests
import time
import os

DATA_FILE = "oraakkeli_categorized.json"
OUTPUT_FILE = "oraakkeli_grammar.json"

# Question types with their expected grammatical cases
GRAMMAR_CATEGORIES = {
    # Yes/No - these are fine as-is, no case matching needed
    "yes_no": "Kyllä/Ei vastaukset (joo, ei, ehkä, totta kai, tuskin)",

    # Nominative case (perusmuoto) - "Mikä on X?" "Kuka on X?"
    "what_nom": "Mikä/Kuka ON vastaukset - nominatiivi (Rakkaus, Koira, Pekka, Elämä)",

    # Genitive case - "Kenen?"
    "who_gen": "Kenen vastaukset - genetiivi (Äidin, Isän, Pekan, Sinun)",

    # Partitive case - "Mitä?" "Ketä?"
    "what_part": "Mitä/Ketä vastaukset - partitiivi (Rakkautta, Ruokaa, Pekkaa)",

    # Allative case - "Kenelle?" "Mille?"
    "who_all": "Kenelle/Mille vastaukset - allatiivi (Äidille, Kaverille, Sinulle)",

    # Ablative case - "Keneltä?" "Miltä?"
    "who_abl": "Keneltä/Miltä vastaukset - ablatiivi (Äidiltä, Kaverilta, Sinulta)",

    # Inessive case - "Missä?"
    "where_ine": "Missä vastaukset - inessiivi (Suomessa, Kotona, Täällä)",

    # Elative case - "Mistä?"
    "where_ela": "Mistä vastaukset - elatiivi (Suomesta, Kotoa, Täältä, Rakkaudesta)",

    # Illative case - "Mihin?" "Minne?"
    "where_ill": "Mihin/Minne vastaukset - illatiivi (Suomeen, Kotiin, Sinne)",

    # Adessive case - "Millä?" (instrument/location)
    "how_ade": "Millä vastaukset - adessiivi (Autolla, Kädellä, Rakkaudella)",

    # Essive case - "Milloin?" (as what/when)
    "when_ess": "Milloin vastaukset - essiivi/aika (Huomenna, Ensi viikolla, 2 päivän päästä)",

    # Translative case - "Miksi?" (become what) - but also "why"
    "why": "Miksi vastaukset - syyt (Koska..., Siksi että..., Sen takia)",

    # How/manner - adverbs
    "how_adv": "Miten/Kuinka vastaukset - adverbit (Nopeasti, Hyvin, Varovasti)",

    # Numbers/counts
    "count": "Montako/Kuinka monta vastaukset - lukumäärät (5, Monta, Paljon)",

    # Time durations
    "time_dur": "Kuinka kauan vastaukset - kestot (2 viikkoa, 10 minuuttia, Ikuisesti)",

    # Other
    "other": "Muut vastaukset"
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
                    time.sleep(5)
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
    """Categorize a batch of answers by grammatical case using AI"""

    answers_text = "\n".join([f"{i+1}. {a}" for i, a in enumerate(answers)])

    prompt = f"""Olet suomen kielen asiantuntija. Kategorisoi nämä oraakkelin vastaukset KIELIOPIN mukaan.

KATEGORIAT (valitse YKSI per vastaus):

yes_no = Kyllä/Ei (joo, ei, ehkä, totta kai, tuskin, ehdottomasti)
what_nom = Nominatiivi - vastaa "Mikä ON?" "Kuka ON?" (Rakkaus, Koira, Pekka, Se on...)
who_gen = Genetiivi - vastaa "Kenen?" (Äidin, Isän, Sinun, Pekan)
what_part = Partitiivi - vastaa "Mitä?" "Ketä?" (Rakkautta, Ruokaa, Pekkaa, Sinua)
who_all = Allatiivi - vastaa "Kenelle?" "Mille?" (Äidille, Sinulle, Kaverille)
who_abl = Ablatiivi - vastaa "Keneltä?" (Äidiltä, Sinulta, Kaverilta)
where_ine = Inessiivi - vastaa "Missä?" (Suomessa, Kotona, Täällä, Sängyssä)
where_ela = Elatiivi - vastaa "Mistä?" (Suomesta, Kotoa, Rakkaudesta)
where_ill = Illatiivi - vastaa "Mihin?" "Minne?" (Suomeen, Kotiin, Sinne, Sänkyyn)
how_ade = Adessiivi - vastaa "Millä?" (Autolla, Kädellä, Rakkaudella)
when_ess = Aika - vastaa "Milloin?" "Koska?" (Huomenna, 2 viikon päästä, Pian, Ensi vuonna)
why = Syy - vastaa "Miksi?" (Koska..., Siksi että..., Sen takia, Sen vuoksi)
how_adv = Tapa - vastaa "Miten?" "Kuinka?" (Nopeasti, Hyvin, Varovasti, Kovaa)
count = Lukumäärä - vastaa "Montako?" (5, 100, Monta, Paljon, Vähän)
time_dur = Kesto - vastaa "Kuinka kauan?" (2 viikkoa, 10 min, Ikuisesti, Aina)
other = Ei sovi mihinkään / monimutkainen lause

VASTAUKSET:
{answers_text}

Vastaa VAIN JSON-muodossa:
{{"1": "yes_no", "2": "what_nom", "3": "who_all", ...}}"""

    result = call_ai(prompt)
    if not result:
        return None

    try:
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
    # Load existing categorized answers
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Flatten all answers
    all_answers = []
    for cat, answers in data.get('categorized', {}).items():
        all_answers.extend(answers)

    # Remove duplicates while preserving order
    seen = set()
    answers = []
    for a in all_answers:
        if a not in seen:
            seen.add(a)
            answers.append(a)

    print(f"Loaded {len(answers)} unique answers")

    # Initialize categorized structure
    categorized = {cat: [] for cat in GRAMMAR_CATEGORIES.keys()}

    # Check for existing progress
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            existing = json.load(f)
            categorized = existing.get('categorized', categorized)
            processed = sum(len(v) for v in categorized.values())
            print(f"Resuming from {processed} already categorized answers")

    # Get already categorized answers
    already_done = set()
    for cat_answers in categorized.values():
        already_done.update(cat_answers)

    remaining = [a for a in answers if a not in already_done]
    print(f"Remaining to categorize: {len(remaining)}")

    if not remaining:
        print("All done!")
        return

    batch_size = 40
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

            # Save progress
            output_data = {
                "categorized": categorized,
                "stats": {cat: len(items) for cat, items in categorized.items()}
            }
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            current_total = sum(len(v) for v in categorized.values())
            print(f"  Saved: {current_total} answers")
        else:
            print(f"  Batch failed")

        time.sleep(2)

    # Final stats
    print("\n=== FINAL STATS ===")
    for cat, items in categorized.items():
        print(f"{cat}: {len(items)}")
    print(f"\nTotal: {sum(len(v) for v in categorized.values())}")

if __name__ == "__main__":
    main()
