import os
import json

from operator import itemgetter
from dotenv import load_dotenv

from analyzer import Analyzer


def main() -> None:

    load_dotenv(override=True)
    use_model = os.environ.get("USE_MODEL")

    features = []
    with open('./features.json') as cache:
        features = json.load(cache)

    # round floats:
    for f in features:
        feats: dict = f['features']
        for key, val in feats.items():
            if isinstance(val, float):
                feats[key] = round(val, 3)

    path = './src/analysis/preprocessing.pkl' if use_model == 'true' else None
    analyzer = Analyzer(path)
    results = analyzer.analyze_prs(features)

    ordered_results = sorted(results, key=itemgetter("effort"), reverse=True)

    # Write to file
    write_to_json(ordered_results, "./results.json")

def write_to_json(data: list, path: str):
    with open(path, "w", encoding="utf-8") as output_file:
        json.dump(data, output_file, indent=2)

main()
