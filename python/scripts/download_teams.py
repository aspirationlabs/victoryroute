import argparse
import tarfile
from pathlib import Path

from huggingface_hub import hf_hub_download


def download_teams(
    format_name: str,
    directory: str,
    output_dir: str,
) -> None:
    repo_id = "jakegrigsby/metamon-teams"
    filename = f"{directory}/{format_name}.tar.gz"

    print(f"Downloading {filename} from {repo_id}...")
    local_path = hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        repo_type="dataset",
    )

    output_path = Path(output_dir) / format_name
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"Extracting teams to {output_path}...")
    with tarfile.open(local_path, "r:gz") as tar:
        members = tar.getmembers()
        team_files = [m for m in members if m.isfile() and "team_" in m.name]
        team_files.sort(key=lambda m: int(m.name.split("team_")[1].split(".")[0]))

        for member in team_files:
            file_obj = tar.extractfile(member)
            if file_obj is None:
                continue

            content = file_obj.read().decode("utf-8")
            team_number = member.name.split("team_")[1].split(".")[0]
            team_file_path = output_path / f"{team_number}.team"
            team_file_path.write_text(content)

        print(f"Extracted {len(team_files)} teams to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download Pokemon teams from HuggingFace dataset"
    )
    parser.add_argument(
        "--format",
        type=str,
        default="gen9ou",
        help="Format to download (e.g., gen9ou, gen1ou)",
    )
    parser.add_argument(
        "--directory",
        type=str,
        default="competitive",
        help="Dataset directory (e.g., competitive, modern_replays, paper_variety)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/teams",
        help="Output directory for team files",
    )

    args = parser.parse_args()

    download_teams(
        format_name=args.format,
        directory=args.directory,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
