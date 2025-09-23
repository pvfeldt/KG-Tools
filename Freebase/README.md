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

The method of querying local Freebase can be found in `sparql_execution.py`. The descriptions below pertain to some of the most frequently used functions.

### 1.1 Retrieval for Entity Label

Path to Freebase query: `KG-Tools/Freebase/query/sparql_execution.py`.

Functions:

| Function                       | Description                                                  |
| ------------------------------ | ------------------------------------------------------------ |
| get_label_with_odbc(entity_id) | Input: entity_id->str<br>Output: entity_label->str<br>**Get the entity label for input entity MID.** |

### 1.2 Retrieval for Single-Hop Neighboring Relations

Path to Freebase query: `KG-Tools/Freebase/query/sparql_execution.py`.

Functions:

| Function                               | Description                                                  |
| -------------------------------------- | ------------------------------------------------------------ |
| get_in_relations_with_odbc(entity_id)  | Input: entity_id->str<br>Output: in_relations->list<br>**(?,e) backward retrieval based on input entity. (Entity is known as the object.)** |
| get_out_relations_with_odbc(entity_id) | Input: entity_id->str<br/>Output: out_relations->list<br/>**(e,?) forward retrieval based on input entity. (Entity is known as the subject.)** |

### 1.3 Retrieval for Single-Hop Neighboring Entities

Path to Freebase query:`KG-Tools/Freebase/query/sparql_execution.py`.

Functions:

| Function                                       | Description                                                  |
| ---------------------------------------------- | ------------------------------------------------------------ |
| get_in_entities_with_odbc(entity_id,relation)  | Input: entity_id->str, relation->str<br>Output: in_entities->list<br>**(?,r,e) backward retrieval based on input entity and relation. (Entity is known as the object.)** |
| get_out_entities_with_odbc(entity_id,relation) | Input: entity_id->str, relation->str<br/>Output: out_entities->list<br/>**(e,r,?) forward retrieval based on input entity and relation. (Entity is known as the subject.)** |

### 1.4 Complex Query

Path to Freebase query: `KG-Tools/Freebase/query/sparql_execution.py`.

Functions:

| Function                       | Description                                                  |
| ------------------------------ | ------------------------------------------------------------ |
| execute_query_with_odbc(query) | Input: query->str<br>Output: entities->list<br>**Execute the SPARQL query to obtain the result entities.** |

## 2 Entity Linking

### 2.1 FACC1 Annotation

Path to entity retrieval: `KG-Tools/Freebase/entity_retrieval`.

FACC1 annotation serves the function of mapping ambiguous entities to existing entities in Freebase, which can be downloaded [here](https://github.com/HXX97/GMT-KBQA/tree/main/data/common_data/facc1). 

After downloading, load the FACC1 annotation with surface_index.

```
from entity_retrieval import surface_index_memory

surface_index = surface_index_memory.EntitySurfaceIndexMemory(
    [facc1_path] + "/entity_list_file_freebase_complete_all_mention",
    [facc1_path] + "/surface_map_file_freebase_complete_all_mention",
    [facc1_path] + "/freebase_complete_all_mention")
    
# [facc1_path] = path to the downloaded FACC1 annotation
```

Enter the entity label to retrieve the corresponding similar entities from Freebase, returned as entity IDs.

```
entity = [entity label]
facc1_cand_entities = surface_index.get_indexrange_entity_el_pro_one_mention([entity],top_k=[top-k value])

# [entity label] = ambiguous input entity
# [top-k value] = top-k entity IDs in the FACC1 annotation
```

An example is provided below.

| Example                                                      |
| ------------------------------------------------------------ |
| **Input:** [entity label] = "Super Bowl", [top-k value]= 5   |
| **Output:** OrderedDict([('m.06x5s', 0.9906230221507211), ('m.01qm4t', 0.002982961395954485), ('m.0g9stbf', 0.002751945623173978), ('m.06x76', 0.0007686633058238005), ('m.0jwt71q', 0.00047929818837192826)]) |

## References

- The Freebase setup follows the [Freebase-Setup repository](https://github.com/dki-lab/Freebase-Setup).
- The `sparql_execution.py` script is adapted from the [ChatKBQA repository](https://github.com/LHRLAB/ChatKBQA/blob/main/executor/sparql_executor.py). The functions have been extended to include neighboring entity retrieval. Additionally, the entity linking based on FACC1 annotations is directly sourced from this work.
- The `ontology` folder is cloned from the [GrailQA repository](https://github.com/dki-lab/GrailQA/tree/main/ontology).
- The download of FACC1 annotation is from the [GMT-KBQA repository](https://github.com/HXX97/GMT-KBQA/tree/main/data/common_data/facc1).
