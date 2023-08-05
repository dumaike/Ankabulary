import requests
import json

api_key = '4996b4ec-219f-411e-9d36-403e40db7a7d'


class ProcessedWord:
    def __init__(self):
        self.word = ""
        self.definition = ""
        self.etymology = ""
        self.part_of_speech = ""


def main():
    word = process_word('voluminous')

    print(f'{word.part_of_speech} - {word.definition} - {word.etymology}')


def process_word(word):
    processed_word = ProcessedWord()

    url = f'https://www.dictionaryapi.com/api/v3/references/collegiate/json/{word}?key={api_key}'
    response_obj = requests.post(url, json={})
    response_txt = response_obj.text
    response_dict = json.loads(response_txt[1:len(response_txt)-1])

    one_definition = response_dict['def'][0]['sseq'][0][0][1]['dt'][0][1]
    formatted_definition = one_definition.replace('{bc}', ': ')
    formatted_definition = remove_synonym_wrappers(formatted_definition)
    formatted_definition = remove_link_wrappers(formatted_definition)
    processed_word.definition = formatted_definition
    processed_word.part_of_speech = response_dict['fl']
    processed_word.etymology = remove_italics_wrappers(
        response_dict['et'][0][1])

    return processed_word


def remove_wrappers(input, wrapper_start, wrapper_end):
    result = input
    while wrapper_start in result:
        start_idx = result.index(wrapper_start)
        end_idx = result.index(wrapper_end, start_idx + len(wrapper_start))
        inner_word = result[start_idx + len(wrapper_start):end_idx]
        result = result[0:start_idx] + \
            inner_word + result[end_idx + len(wrapper_end):]

    return result


def remove_link_wrappers(input):
    return remove_wrappers(input, '{a_link|', '}')


def remove_synonym_wrappers(input):
    return remove_wrappers(input, '{sx|', '||}')


def remove_italics_wrappers(input):
    return remove_wrappers(input, '{it}', '{/it}')


main()
