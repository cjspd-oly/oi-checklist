import argparse
import json
import yaml
from pathlib import Path

def infer_stage_from_filename(filename):
    """Convert filename to stage by replacing underscores with spaces and removing .yaml extension"""
    return filename.replace("_", " ").replace(".yaml", "")

def load_scores_json(dir_path: Path, stage: str):
    """
    Looks for a file named scores_<stage>.json in the same directory.
    If found, loads and returns its contents, else returns None.
    """
    stage_json_name = f"scores_{stage.replace(' ', '_')}.json"
    scores_path = dir_path / stage_json_name
    if scores_path.exists():
        with open(scores_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def main():
    parser = argparse.ArgumentParser(description="Convert contest YAML files to flat JSON format")
    parser.add_argument("input_dir", nargs="?", default=".", help="Directory containing contest YAML files")
    parser.add_argument("-o", "--output", default="data.json", help="Output JSON file path")
    args = parser.parse_args()

    input_path = Path(args.input_dir)
    contests = []

    for source_dir in input_path.iterdir():
        if not source_dir.is_dir():
            continue
        source = source_dir.name
        for year_dir in source_dir.iterdir():
            if year_dir.is_file() and year_dir.suffix == ".yaml":
                # Format: source/year.yaml
                year = int(year_dir.stem)
                stage = infer_stage_from_filename(year_dir.name)
                with open(year_dir, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if not isinstance(data, list):
                        raise ValueError(f"Expected list in {year_dir}")
                    scores_data = load_scores_json(year_dir.parent, stage)
                    for contest in data:
                        contest["source"] = source.upper()
                        contest["year"] = year
                        contest["stage"] = stage
                        if scores_data:
                            contest["scores"] = scores_data
                        contests.append(contest)
            elif year_dir.is_dir():
                # Format: source/year/stage.yaml
                year = int(year_dir.name)
                for yaml_file in year_dir.glob("*.yaml"):
                    stage = infer_stage_from_filename(yaml_file.name)
                    with open(yaml_file, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                        if not isinstance(data, list):
                            raise ValueError(f"Expected list in {yaml_file}")
                        scores_data = load_scores_json(yaml_file.parent, stage)
                        for contest in data:
                            contest["source"] = source.upper()
                            contest["year"] = year
                            contest["stage"] = stage
                            if scores_data:
                                contest["scores"] = scores_data
                            contests.append(contest)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(contests, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(contests)} contests → {args.output}")

if __name__ == "__main__":
    main()
