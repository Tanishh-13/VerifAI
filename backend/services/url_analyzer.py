import requests
from bs4 import BeautifulSoup


def analyze_url(url: str) -> dict:

    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            },
            timeout=15
        )

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        title = ""
        description = ""
        image = None
        video = None

        # Open Graph metadata
        og_title = soup.find("meta", property="og:title")
        og_description = soup.find("meta", property="og:description")
        og_image = soup.find("meta", property="og:image")
        og_video = soup.find("meta", property="og:video")

        if og_title:
            title = og_title.get("content", "")

        if og_description:
            description = og_description.get("content", "")

        if og_image:
            image = og_image.get("content")

        if og_video:
            video = og_video.get("content")

        # Fallback to normal HTML title
        if not title and soup.title:
            title = soup.title.get_text(" ", strip=True)

        # Extract visible page text
        for element in soup([
            "script",
            "style",
            "noscript",
            "header",
            "footer",
            "nav"
        ]):
            element.decompose()

        page_text = soup.get_text(
            " ",
            strip=True
        )

        # Avoid sending an enormous webpage to the LLM
        page_text = page_text[:10000]

        combined_text = "\n".join(
            part for part in [
                title,
                description,
                page_text
            ]
            if part
        )

        return {
            "url": url,
            "title": title,
            "description": description,
            "text": combined_text,
            "image": image,
            "video": video,
            "status": "success"
        }

    except Exception as e:

        return {
            "url": url,
            "title": "",
            "description": "",
            "text": "",
            "image": None,
            "video": None,
            "status": "failed",
            "error": str(e)
        }