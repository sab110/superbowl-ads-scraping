import requests

def download_file(url: str, save_path: str):
    """
    Download the file from `url` and save it to `save_path`.
    """
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # raise exception for HTTP errors

        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:  # filter out keep-alive chunks
                    f.write(chunk)
        print(f"File downloaded and saved to {save_path}")
    except Exception as e:
        print(f"Error downloading file: {e}")

if __name__ == "__main__":
    url = "https://www.unblock.coffee/wp-content/uploads/2025/06/Lucky-Yatra-6.avif"
    save_path = "Lucky-Yatra-6.avif"
    download_file(url, save_path)
