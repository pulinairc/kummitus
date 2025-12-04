#!/usr/bin/env python3
"""
Scrape all unique Q&A pairs from oraakkeli.app
Run: screen -S oraakkeli python3 oraakkeli_scraper.py
"""
import requests
import re
import random
import time
import json
import os

OUTPUT_FILE = "/home/rolle/.sopel/modules/oraakkeli_data.json"

def load_data():
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"answers": [], "questions": []}

def save_data(data):
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_qa(question):
    rnd = random.randint(10000000, 99999999)

    try:
        response = requests.get(
            "https://oraakkeli.app/",
            params={
                f"kysymys_{rnd}": question,
                "submit": "",
                "rnd": rnd
            },
            timeout=10
        )

        if response.status_code == 200:
            match = re.search(r"<p class='vastaus'>([^<]+)</p>", response.text)
            if match:
                return match.group(1).strip()
    except Exception as e:
        print(f"Error: {e}")

    return None

def main():
    data = load_data()
    answers = set(data["answers"])
    questions = set(data["questions"])
    print(f"Loaded {len(answers)} answers, {len(questions)} questions")

    # Comprehensive Finnish question words and verb forms
    question_templates = [
        # Basic interrogatives (kysymyssanat)
        "mikä", "mitä", "mitkä", "kuka", "ketkä", "ketä", "kenet",
        "missä", "mistä", "mihin", "minne", "millä", "miltä", "mille",
        "miksi", "milloin", "miten", "kuinka", "kumpi",
        "millainen", "minkälainen", "minkä",
        # -ko/-kö verb questions
        "onko", "olenko", "oletko", "onkos", "eikö", "eiköhän",
        "voiko", "voinko", "voitko", "voimmeko",
        "saako", "saanko", "saatko",
        "pitääkö", "pitäisikö", "täytyykö",
        "kannattaako", "kannattaisiko",
        "tuleeko", "tulenko", "tuletko",
        "haluanko", "haluatko", "haluaako",
        "uskallanko", "uskaltaako",
        "osanko", "osaatko", "osaako",
        "tiedätkö", "tiedänkö", "tietääkö",
        "muistatko", "muistanko",
        "rakastatko", "rakastaako",
        "vihaavatko", "vihaatko",
        "kelpaako", "riittääkö", "mahtuuko", "sopiiko",
        "auttaako", "toimiiko", "onnistuuko",
        "näkyykö", "kuuluuko", "tuntuuko",
        "löytyykö", "löydänkö",
        "pärjäänkö", "selviänkö",
        # Common question phrases
        "mitäs", "mikäs", "kukas", "entäs", "entäpä",
        "paljonko", "montako", "kuinka paljon", "kuinka monta",
        "koska", "kauanko", "kuinka kauan",
        "kenelle", "keneltä", "kenellä", "kenen",
        "minkä takia", "minkä vuoksi", "mistä syystä"
    ]

    try:
        i = 0
        while True:
            question = random.choice(question_templates)
            answer = fetch_qa(question)

            new_answer = answer and answer not in answers
            new_question = question not in questions

            if new_answer:
                answers.add(answer)
                print(f"[A:{len(answers)} Q:{len(questions)}] NEW ANSWER: {answer}")

            if new_question:
                questions.add(question)

            if new_answer or new_question:
                data["answers"] = sorted(list(answers))
                data["questions"] = sorted(list(questions))
                save_data(data)
            else:
                i += 1
                if i % 10 == 0:
                    print(f"[A:{len(answers)} Q:{len(questions)}] Still searching...")

            time.sleep(10)

    except KeyboardInterrupt:
        print(f"\nStopped. Total: {len(answers)} answers, {len(questions)} questions")
        data["answers"] = sorted(list(answers))
        data["questions"] = sorted(list(questions))
        save_data(data)

if __name__ == "__main__":
    main()
