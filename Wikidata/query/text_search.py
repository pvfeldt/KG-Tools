import wikipediaapi

def link_wikipedia():
    wikipedia = wikipediaapi.Wikipedia(
        user_agent='agent',
        language='en',
        extract_format=wikipediaapi.ExtractFormat.WIKI
    )
    return wikipedia

wikipedia=link_wikipedia()

# section=[section xxx: xxx,section xxx: xxx]
def extract_section_key(section_lists):
    # section_dict={"key":{"subkey":xxx}}
    section_dict={}
    for section_text in section_lists:
        key=section_text.title.strip()
        level=section_text.level
        full_text=section_text.full_text(level).strip()
        section_dict[key]=full_text.replace(key+"\n","")
    return section_dict


def search_in_wikipedia(keyword):
    p_wiki=wikipedia.page(keyword)
    summary=p_wiki.summary
    section_list=p_wiki.sections
    section_dict={}
    section_dict["summary"]=summary
    section_dict.update(extract_section_key(section_list))
    return section_dict
