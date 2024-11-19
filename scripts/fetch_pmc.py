import requests
import xml.etree.ElementTree as ET
import csv
from datetime import datetime, timedelta


def fetch_pmc_articles(search_terms, days=7, max_results=100):
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

    # Get the date range for the last week
    end_date = datetime.now().strftime("%Y/%m/%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")

    # Construct the search query
    search_query = f"({' OR '.join(search_terms)}) AND {start_date}:{end_date}[PDAT]"

    # First, search for PMCIDs
    search_url = f"{base_url}esearch.fcgi?db=pmc&term={search_query}&retmax={max_results}&usehistory=y"
    search_response = requests.get(search_url)
    search_root = ET.fromstring(search_response.content)

    # Extract WebEnv and QueryKey
    web_env = search_root.find("WebEnv").text
    query_key = search_root.find("QueryKey").text

    # Now, fetch the details for these PMCIDs
    fetch_url = f"{base_url}efetch.fcgi?db=pmc&query_key={query_key}&WebEnv={web_env}&retmax={max_results}&retmode=xml"
    fetch_response = requests.get(fetch_url)
    fetch_root = ET.fromstring(fetch_response.content)

    articles = []
    for article in fetch_root.findall(".//article"):
        pmcid = article.find(".//article-id[@pub-id-type='pmc']").text
        title = article.find(".//article-title").text
        abstract = article.find(".//abstract/p")
        abstract_text = (
            abstract.text if abstract is not None else "No abstract available"
        )

        articles.append({"PMCID": pmcid, "Title": title, "Abstract": abstract_text})

    return articles


def save_to_csv(articles, filename):
    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["PMCID", "Title", "Abstract"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for article in articles:
            writer.writerow(article)


if __name__ == "__main__":
    search_terms = [
        "medicine",
        "biomedical sciences",
        "clinical therapies",
        "treatments",
        "healthcare",
        "drug discovery",
        "medical diagnostics",
        "patient care",
        "disease prevention",
        "public health",
        "medical technology",
        "personalized medicine",
        "clinical trials",
        "medical imaging",
        "genomics",
    ]

    articles = fetch_pmc_articles(search_terms)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"pmc_medical_articles_{timestamp}.csv"
    save_to_csv(articles, filename)
    print(f"Saved {len(articles)} articles to {filename}")
