# Freebase

## 0 Local Setup

Detailed instructions for downloading and setting up Freebase in Virtuoso are available [here](https://github.com/dki-lab/Freebase-Setup). 

Clone the setup repository and start up the service with the following instruction.

```
cd Freebase-Setup
python3 virtuoso.py start 3001 -d [/path/to/virtuoso/db/files]
```

Close the service as follows.

```
python3 virtuoso.py stop 3001
```

## 1 Query

The method of querying local Freebase can be found in sparql_execution.py. The descriptions below pertain to some of the most frequently used functions.

### 1.1 Retrieval for Entity Label

Path to Freebase query:

```
./KG-Tools/freebase/query/sparql_execution.py
```

Functions:

| Function                       | Description                                                  |
| ------------------------------ | ------------------------------------------------------------ |
| get_label_with_odbc(entity_id) | Input: entity_id->str<br>Output: entity_label->str<br>**Get the entity label for input entity MID.** |

### 1.2 Retrieval for Single-Hop Neighboring Relations

Path to Freebase query:

```
./KG-Tools/freebase/query/sparql_execution.py
```

Functions:

| Function                               | Description                                                  |
| -------------------------------------- | ------------------------------------------------------------ |
| get_in_relations_with_odbc(entity_id)  | Input: entity_id->str<br>Output: in_relations->list<br>**(?,e) backward retrieval based on input entity. (Entity is known as the object.)** |
| get_out_relations_with_odbc(entity_id) | Input: entity_id->str<br/>Output: out_relations->list<br/>**(e,?) forward retrieval based on input entity. (Entity is known as the subject.)** |

### 1.3 Retrieval for Single-Hop Neighboring Entities

Path to Freebase query:

```
./KG-Tools/freebase_query/sparql_execution.py
```

Functions:

| Function                                       | Description                                                  |
| ---------------------------------------------- | ------------------------------------------------------------ |
| get_in_entities_with_odbc(entity_id,relation)  | Input: entity_id->str, relation->str<br>Output: in_entities->list<br>**(?,r,e) backward retrieval based on input entity and relation. (Entity is known as the object.)** |
| get_out_entities_with_odbc(entity_id,relation) | Input: entity_id->str, relation->str<br/>Output: out_entities->list<br/>**(e,r,?) forward retrieval based on input entity and relation. (Entity is known as the subject.)** |

### 1.4 Complex Query

Path to Freebase query:

```
./KG-Tools/freebase_query/sparql_execution.py
```

Functions:

| Function                       | Description                                                  |
| ------------------------------ | ------------------------------------------------------------ |
| execute_query_with_odbc(query) | Input: query->str<br>Output: entities->list<br>**Execute the SPARQL query to obtain the result entities.** |

## 2 Other Related

### 2.1 FACC1 Annotation

FACC1 annotation serves the function of mapping ambiguous entities to existing entities in Freebase, which can be downloaded [here](https://github.com/HXX97/GMT-KBQA/tree/main/data/common_data/facc1).
