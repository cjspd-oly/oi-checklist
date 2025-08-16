import argparse
import json
import yaml
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Convert YAML directory structure into flat JSON")
    parser.add_argument("input_dir", help="Root directory (e.g. data/)")
    parser.add_argument("--output", default="data.json", help="Output JSON file")
    args = parser.parse_args()

    input_path = Path(args.input_dir)
    all_problems = []

    for source_dir in input_path.iterdir():
        if not source_dir.is_dir():
            continue

        for year_path in source_dir.iterdir():
            if year_path.is_file() and year_path.suffix == ".yaml":
                year = int(year_path.stem)
                extra = None
                yaml_files = [(year_path, year, extra)]
            elif year_path.is_dir():
                year = int(year_path.name)
                yaml_files = [(p, year, p.stem.replace("_", " ")) for p in year_path.glob("*.yaml")]
            else:
                continue

            for yaml_path, year, extra in yaml_files:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    problems = yaml.safe_load(f) or []

                for problem in problems:
                    problem["source"] = source_dir.name.upper()
                    problem["year"] = year
                    if extra:
                        problem["extra"] = extra
                    all_problems.append(problem)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(all_problems, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(all_problems)} problems to {args.output}")

if __name__ == "__main__":
    main()