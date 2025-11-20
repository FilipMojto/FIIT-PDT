from elasticsearch import Elasticsearch, helpers

class ElasticCRUD:
    def __init__(self, url="http://localhost:9200"):
        self.es = Elasticsearch(url)

    # -------------------------
    # CREATE ONE DOCUMENT
    # -------------------------
    def create_doc(self, index, doc_id, body):
        return self.es.index(index=index, id=doc_id, document=body)

    # -------------------------
    # READ ONE DOCUMENT
    # -------------------------
    def get_doc(self, index, doc_id):
        try:
            return self.es.get(index=index, id=doc_id)
        except:
            return None

    # -------------------------
    # UPDATE ONE DOCUMENT
    # -------------------------
    def update_doc(self, index, doc_id, fields):
        return self.es.update(index=index, id=doc_id, doc={"doc": fields})

    # -------------------------
    # DELETE ONE DOCUMENT
    # -------------------------
    def delete_doc(self, index, doc_id):
        return self.es.delete(index=index, id=doc_id)

    # -------------------------
    # DELETE ALL DOCUMENTS IN INDEX (WITHOUT DROPPING INDEX)
    # -------------------------
    def delete_all_docs(self, index):
        return self.es.delete_by_query(
            index=index,
            body={"query": {"match_all": {}}},
            refresh=True
        )

    # -------------------------
    # DELETE ENTIRE INDEX
    # -------------------------
    def drop_index(self, index):
        if self.es.indices.exists(index=index):
            return self.es.indices.delete(index=index)
        return {"acknowledged": True, "message": "index did not exist"}

    # -------------------------
    # INSERT BULK DOCUMENTS
    # -------------------------
    def bulk_insert(self, index, docs):
        actions = [
            {"_index": index, "_source": doc}
            for doc in docs
        ]
        helpers.bulk(self.es, actions)
        return {"status": "OK", "count": len(actions)}


# -------------------------
# Example usage
# -------------------------
if __name__ == "__main__":
    crud = ElasticCRUD()

    # Create a document
    # print(crud.create_doc("tweets", "1", {"text": "Hello world"}))

    # # Read it
    # print(crud.get_doc("tweets", "1"))

    # # Update it
    # print(crud.update_doc("tweets", "1", {"text": "New content"}))

    # # Delete a single document
    # print(crud.delete_doc("tweets", "1"))

    # Delete all documents
    # print(crud.delete_all_docs("tweets"))

    # Drop index completely
    print(crud.drop_index("tweets"))
