class BaseSource:
    def search(self, query: str, limit: int = 1000):
        raise NotImplementedError

    def get_by_doi(self, doi: str):
        raise NotImplementedError

    def normalize(self, raw_item):
        raise NotImplementedError
