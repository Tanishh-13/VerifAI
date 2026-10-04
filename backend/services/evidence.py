import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


def search_news(query: str, max_records: int = 8) -> list:

    if not query or not query.strip():
        return []

    encoded_query = urllib.parse.quote(query.strip())

    url = (
        "https://news.google.com/rss/search?"
        f"q={encoded_query}"
        "&hl=en-IN"
        "&gl=IN"
        "&ceid=IN:en"
    )

    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        with urllib.request.urlopen(request, timeout=15) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)

    except Exception as e:
        return [{
            "error": "Unable to retrieve live news evidence",
            "details": str(e)
        }]

    articles = []
    seen = set()

    for item in root.findall(".//item"):

        title = item.findtext("title")
        link = item.findtext("link")
        published = item.findtext("pubDate")
        source = item.findtext("source")

        title = (title or "").strip()
        link = (link or "").strip()
        published = (published or "").strip()
        source = (source or "").strip()

        if not title:
            continue

        # Avoid duplicate headlines/articles
        dedup_key = (
            title.lower(),
            source.lower()
        )

        if dedup_key in seen:
            continue

        seen.add(dedup_key)

        articles.append({
            "title": title,
            "url": link,
            "source": source,
            "published": published
        })

        if len(articles) >= max_records:
            break

    return articles