"""
Generate submission.jsonl for the Magicpin Vera AI Challenge.

Runs the composition engine over the 30 canonical test pairs in expanded/test_pairs.json
and writes submission.jsonl.
"""

import json
from pathlib import Path
from bot import compose


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    base_dir = Path(__file__).parent / "expanded"
    if not base_dir.exists():
        print(f"Error: {base_dir} does not exist. Run generate_dataset.py first.")
        return

    pairs_file = base_dir / "test_pairs.json"
    if not pairs_file.exists():
        print(f"Error: {pairs_file} not found.")
        return

    test_pairs = load_json(pairs_file).get("pairs", [])
    print(f"Generating submission.jsonl for {len(test_pairs)} test pairs...")

    output_file = Path(__file__).parent / "submission.jsonl"
    lines = []

    for pair in test_pairs:
        test_id = pair["test_id"]
        trg_id = pair["trigger_id"]
        merchant_id = pair["merchant_id"]
        customer_id = pair.get("customer_id")

        trigger = load_json(base_dir / "triggers" / f"{trg_id}.json")
        merchant = load_json(base_dir / "merchants" / f"{merchant_id}.json")
        cat_slug = merchant.get("category_slug")
        category = load_json(base_dir / "categories" / f"{cat_slug}.json")
        
        customer = None
        if customer_id:
            cust_path = base_dir / "customers" / f"{customer_id}.json"
            if cust_path.exists():
                customer = load_json(cust_path)

        res = compose(category, merchant, trigger, customer)
        
        entry = {
            "test_id": test_id,
            "body": res["body"],
            "cta": res["cta"],
            "send_as": res["send_as"],
            "suppression_key": res["suppression_key"],
            "rationale": res["rationale"]
        }
        lines.append(json.dumps(entry, ensure_ascii=False))

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Successfully generated {len(lines)} lines in {output_file}")


if __name__ == "__main__":
    main()
