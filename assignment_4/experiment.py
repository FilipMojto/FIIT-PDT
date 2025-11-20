from elasticsearch import Elasticsearch
from argparse import ArgumentParser
import time

parser = ArgumentParser(description="Elasticsearch CRUD + SEARCH tester")
parser.add_argument("--es-url", type=str, default="http://localhost:9200",
                    help="Elasticsearch URL")
parser.add_argument("--index", type=str, default="tweets",
                    help="Elasticsearch index name")
args = parser.parse_args()


class ElasticCRUD:
    def __init__(self, url="http://localhost:9200"):
        self.es = Elasticsearch(url)

    def create_doc(self, index, doc_id, body):
        return self.es.index(index=index, id=doc_id, document=body)

    def get_doc(self, index, doc_id):
        try:
            return self.es.get(index=index, id=doc_id)
        except:
            return None

    def update_doc(self, index, doc_id, fields):
        return self.es.update(index=index, id=doc_id, body={"doc": fields})

    def delete_doc(self, index, doc_id):
        return self.es.delete(index=index, id=doc_id)

    def search_docs(self, index, query):
        return self.es.search(index=index, body=query)

    def create_index_if_missing(self, index):
        if not self.es.indices.exists(index=index):
            print(f"Index '{index}' does not exist. Creating...")
            self.es.indices.create(index=index)
            time.sleep(1)


if __name__ == "__main__":

    es_crud = ElasticCRUD(url=args.es_url)
    index_name = args.index

    # ---------------------------------------------------------
    # 1) Ensure index exists
    # ---------------------------------------------------------
    es_crud.create_index_if_missing(index_name)

    print("\n===== CREATE (C) =====")
    es_crud.create_doc(index_name, "1", {"text": "Covid cases rise again"})
    es_crud.create_doc(index_name, "2", {"text": "People discuss vaccines"})
    es_crud.create_doc(index_name, "3", {"text": "Holiday season is coming"})
    print("Inserted 3 documents.")

    time.sleep(1)

    print("\n===== READ (R) =====")
    print(es_crud.get_doc(index_name, "1"))

    print("\n===== UPDATE (U) =====")
    es_crud.update_doc(index_name, "1", {"text": "Covid cases are rising again"})
    print(es_crud.get_doc(index_name, "1"))

    print("\n===== SEARCH =====")
    query = {
        "query": { "match": { "text": "covid" } }
    }
    results = es_crud.search_docs(index_name, query)
    print("Search results (match 'covid'):")
    print(results["hits"]["hits"])

    print("\n===== DELETE (D) =====")
    es_crud.delete_doc(index_name, "2")
    print("Doc 2 deleted. Checking:")
    print(es_crud.get_doc(index_name, "2"))

    time.sleep(1)

    print("\n===== FINAL SEARCH (all docs) =====")
    all_docs = es_crud.search_docs(index_name, {"query": {"match_all": {}}})
    # print(all_docs["hits"]["hits"])
    for hit in all_docs["hits"]["hits"]:
        print(hit["_source"]["full_text"])

    
    print("Filtering retweets only (RT @...)")
    query = {
        "query": {
            "match": {
                "full_text": "RT @"
            }
        }
    }
    rt_docs = es_crud.search_docs(index_name, query)
    for hit in rt_docs["hits"]["hits"]:
        print(hit["_source"]["full_text"])

    # updating a single document

    # first we fetch the original document
    print("\n===== UPDATE single document =====")
    doc = es_crud.get_doc(index_name, "1")

    update_docs = es_crud.update_doc(
        index_name,
        "1",
        {
            "favorite_count": 10,
            "retweet_count": 5
        }
    )

    print("Updated document:")
    print(es_crud.get_doc(index_name, "1"))

    print("\n===== DONE =====")