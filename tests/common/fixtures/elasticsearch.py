# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

import pytest

from h import search

ELASTICSEARCH_INDEX = "hypothesis-test"
ELASTICSEARCH_URL = os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200")


@pytest.fixture
def es_client():
    client = _es_client()
    yield client
    client.conn.delete_by_query(
        index=client.index,
        body={"query": {"match_all": {}}},
        # This query occassionally fails with a version conflict.
        # This happens during tests that update/delete annotations.
        # See https://www.elastic.co/guide/en/elasticsearch/reference/current/docs-delete-by-query.html#docs-delete-by-query.
        # Regardless of what happened during the test, all annotations should be removed from the index.
        conflicts="proceed",
        # Add refresh to propogate the mark for deletion to all shards.
        refresh=True,
    )


@pytest.fixture(scope="session", autouse=True)
def init_elasticsearch(request):
    """
    Initialize the elasticsearch cluster.

    Connect to the instance of Elasticsearch and initialize the index
    once per test session and delete the index after the test is completed.
    """
    es_client = _es_client()

    def maybe_delete_index():
        """Delete the test index if it exists."""
        if es_client.conn.indices.exists(index=ELASTICSEARCH_INDEX):
            # The delete operation must be done on a concrete index, not an alias
            # in ES6. See https://www.elastic.co/guide/en/elasticsearch/reference/current/indices-delete-index.html
            concrete_indexes = es_client.conn.indices.get(index=ELASTICSEARCH_INDEX)
            for index in concrete_indexes:
                es_client.conn.indices.delete(index=index)

    # Delete the test search index at the end of the test run.
    request.addfinalizer(maybe_delete_index)

    # Delete the test search index at the start of the run, just in case it
    # was somehow left behind by a previous test run.
    maybe_delete_index()

    # Initialize the test search index.
    search.init(es_client)


def _es_client():
    return search.get_client(
        {"es.url": ELASTICSEARCH_URL, "es.index": ELASTICSEARCH_INDEX}
    )
