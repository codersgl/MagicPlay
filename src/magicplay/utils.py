from pathlib import Path

import requests
from tqdm import tqdm


class Utils:
    @staticmethod
    def get_prompt(source: str | Path) -> str:
        path = Path(source)
        file_to_read = None

        if path.exists() and path.is_file():
            file_to_read = path
        elif path.exists() and path.is_dir():
            match = sorted(list(path.rglob("*.md")))
            if not match:
                raise FileNotFoundError(f"No .md files found in {path}")
            file_to_read = match[0]
            if len(match) > 1:
                print(
                    f"Found multiple prompt files, using the first one: {file_to_read}"
                )
        else:
            raise FileNotFoundError(f"Path not found: {path}")

        try:
            with open(file_to_read, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            raise RuntimeError(f"Failed to read prompt file {file_to_read}: {e}")

    @staticmethod
    def download_video(url: str, save_path: str | Path):
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))

            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)

            with open(save_path, "wb") as f:
                if total_size == 0:
                    f.write(response.content)
                    print(f"Download complete: {save_path.name}")
                else:
                    with tqdm(
                        total=total_size,
                        unit="B",
                        unit_scale=True,
                        desc=save_path.name,
                        unit_divisor=1024,
                    ) as pbar:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                pbar.update(len(chunk))

                    print(
                        f"Finished downloading, file size: {total_size / 1024 / 1024:.2f} MB"
                    )

            return True

        except requests.exceptions.RequestException as e:
            print(f"Download failed: {e}")
            raise  # Re-raise exception to let caller handle it
