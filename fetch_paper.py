import requests
import json

# Define the API endpoint URL
url = "https://api.semanticscholar.org/recommendations/v1/papers"


def load_paper_list():
    with open('papers.json', 'r') as output:
        return json.load(output)


def save_paper_list(papers):
    with open('papers.json', 'w') as output:
        json.dump(papers, output)


def fetch_paper(papers):
    # Define the query parameters
    query_params = {
        "fields": "citationCount,abstract",
        "limit": "5"
    }
    # Define the request data
    paper_ids = []
    for paper in papers:
        paper_ids.append(paper["paperId"])
    data = {
        "positivePaperIds": paper_ids,
    }
    # Directly define the API key (Reminder: Securely handle API keys in production environments)
    # api_key = "your api key goes here"  # Replace with the actual API key
    #
    # Define headers with API key
    # headers = {"x-api-key": api_key}
    # Send the API request
    response = requests.post(url, params=query_params, json=data).json()
    # Sort the recommended papers by citation count
    papers = response["recommendedPapers"]
    papers.sort(key=lambda paper: paper["citationCount"], reverse=True)
    # print(papers)
    # with open('papers.json', 'w') as output:
    #     json.dump(papers, output)
    return papers


if __name__ == '__main__':
    papers = load_paper_list()
    print(fetch_paper(papers))
