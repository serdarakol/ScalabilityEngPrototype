import argparse
import json
import random
import string
from pathlib import Path

def random_string(length=25):
    """Generate a random alphanumeric string with spaces."""
    chars = string.ascii_letters + string.digits + "     "  # include spaces
    return ''.join(random.choice(chars) for _ in range(length)).strip()

def generate_species_data(count, seed=None):
    if seed is not None:
        random.seed(seed)
    data = []
    for i in range(1, count + 1):
        record = {
            "id": str(i),
            "name": f"Species-{i}",
            "info": random_string(100)
        }
        data.append(record)
    return data

def main():
    parser = argparse.ArgumentParser(description="Generate species seed JSON file")
    parser.add_argument("--count", type=int, default=100, help="Number of species records to generate")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--output", type=str, default="src/server/species_seed.json", help="Output JSON file path")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    species = generate_species_data(args.count, args.seed)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(species, f, indent=2)

    print(f"Generated {len(species)} species records at '{output_path}'")

if __name__ == "__main__":
    main()
