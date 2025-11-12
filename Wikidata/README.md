# Wikidata

## 0 Setup

### 0.1 Online Query API

Visit [offical Wikidata Online Query](https://query.wikidata.org/) to perform a direct online query.

### 0.2 Local Implementation using the Online Query Service

To access the API locally, a tool is provided in the `KG-Tools/Wikidata/query` folder that enables storage-free online queries and simplifies data retrieval. Detailed instructions are available in the Query Section below.

The APIs below include the official endpoint and another stable endpoint.

| API Type                         | Link                                                        |
| -------------------------------- | ----------------------------------------------------------- |
| Official Wikidata Online Service | [Official Endpoint Link](https://query.wikidata.org/sparql) |
| Stable Endpoint                  | [Stable Endpoint Link](https://skynet.coypu.org/wikidata/)  |

### 0.3 Local Implementation of the Latest Database

Due to the high storage requirements for implementing Wikidata dataset locally, we only provide the download link here.

| Database          | Link                                                         |
| ----------------- | ------------------------------------------------------------ |
| Wikidata Database | [Download Link](https://dumps.wikimedia.org/wikidatawiki/entities/) |

### 0.4 Entity Mapping

Wikidata includes some of the knowledge graphs from Freebase. The entity mapping file can be downloaded using the link below. We also provide the mapping functions (Freebase to Wikidata & Wikidata to Freebase) in the `KG-Tools/Wikidata/query` folder.

| Mapping File                | Link                                                         |
| --------------------------- | ------------------------------------------------------------ |
| Freebase to Wikidata (fb2w) | [Download Link](https://developers.google.com/freebase?hl=zh-cn#freebase-wikidata-mappings) |

## 1 Query

The method for querying Wikidata can be found in `sparql_execution.py` and `sparql_query_combined.py`. The descriptions below pertain to some of the most commonly used functions.

**Note:** `sparql_execution.py` queries only the official endpoint, while `sparql_query_combined.py` accesses both the official and stable endpoints. In cases where failures occur when accessing the official endpoint, `sparql_query_combined.py` (which queries the stable endpoint first and uses proxies for the official endpoint, though it may not always be stable) serves as a backup method.

### 1.1 Retrieval for Entity/ Relation Labels and IDs

Path to Wikidata query: `KG-Tools/Wikidata/query/sparql_execution.py` and `KG-Tools/Wikidata/query/sparql_execution_combined.py`.

Functions:

| Function                                              | Description                                                  |
| ----------------------------------------------------- | ------------------------------------------------------------ |
| get_label(entity_id)<br>get_label_combined(entity_id) | Input: entity_id->str<br>Output: entity_label->str<br>**Get the entity/ relation label for input entity QID/ relation PID .** |
| get_id(entity_label)<br>get_id_combined(entity_label) | Input: entity_label->str<br/>Output: entity_ids->list<br/>**Get the entity QIDs/ relation PIDs for input entity/ relation label. (A label might be mapped to a series of IDs)** |

### 1.2 Retrieval for Single-Hop Neighboring Relations

Path to Wikidata query: `KG-Tools/Wikidata/query/sparql_execution.py` and `KG-Tools/Wikidata/query/sparql_execution_combined.py`.

Functions:

| Function                                                     | Description                                                  |
| ------------------------------------------------------------ | ------------------------------------------------------------ |
| get_in_relations(entity_id)<br>get_in_relations_combined(entity_id) | Input: entity_id->str<br>Output: in_relations->dict {"Pxxx":"xxx"}<br>**(?,e) backward retrieval based on input entity. (Entity is known as the object.)** |
| get_out_relations(entity_id)<br>get_out_relations_combined(entity_id) | Input: entity_id->str<br/>Output: out_relations->dict {"Pxxx":"xxx"}<br/>**(e,?) forward retrieval based on input entity. (Entity is known as the subject.)** |

### 1.3 Retrieval for Single-Hop Neighboring Entities

Path to Wikidata query: `KG-Tools/Wikidata/query/sparql_execution.py` and `KG-Tools/Wikidata/query/sparql_execution_combined.py`.

Functions:

| Function                                                     | Description                                                  |
| ------------------------------------------------------------ | ------------------------------------------------------------ |
| get_in_entities(entity_id,relation_id)<br>get_in_entities_combined(entity_id,relation_id) | Input: entity_id->str, relation_id->str<br>Output: in_entities->dict {"Qxxx":"xxx"}<br>**(?,r,e) backward retrieval based on input entity and relation. (Entity is known as the object.)** |
| get_out_entities(entity_id,relation_id)<br>get_out_entities_combined(entity_id,relation_id) | Input: entity_id->str, relation_id->str<br/>Output: out_entities->dict {"Qxxx":"xxx"}<br/>**(e,r,?) forward retrieval based on input entity and relation. (Entity is known as the subject.)** |

### 1.4 Complex Query

Path to Wikidata query: `KG-Tools/Wikidata/query/sparql_execution.py` and `KG-Tools/Wikidata/query/sparql_execution_combined.py`.

| Function                                                     | Description                                                  |
| ------------------------------------------------------------ | ------------------------------------------------------------ |
| execute_query(query)<br>execute_query_combined(query)        | Input: query->str<br>Output: entities->list ["Qxxx"]<br>**Execute the SPARQL query to obtain the result entities.** |
| execute_query_with_label(query)<br/>execute_query_with_label_combined(query) | Input: query->str<br/>Output: entities->dict {"Qxxx":"xxx"}<br/>**Execute the SPARQL query to obtain the result entities.** |

### 1.5 Entity Mapping between Freebase and Wikidata

Path to Wikidata query: `KG-Tools/Wikidata/query/sparql_execution.py` and `KG-Tools/Wikidata/query/sparql_execution_combined.py`.

| Function                      | Description                                                  |
| ----------------------------- | ------------------------------------------------------------ |
| map_freebase_to_wikidata(MID) | Input: MID->str<br>Output: QID->dict {"Qxxx":"xxx"}<br>**Map Freebase MID to Wikidata QID.** |
| map_wikidata_to_freebase(QID) | Input: QID->str<br/>Output: MID->str "m.xxx"<br/>**Map Wikidata QID to Freebase MID.** |

## References

- The official online query API is accessible via the [Wikidata Query Service](https://query.wikidata.org/sparql). 
- Another stable endpoint is  [Wikidata endpoint](https://skynet.coypu.org/wikidata/), provided by [QALD-10](https://github.com/KGQA/QALD-10).

