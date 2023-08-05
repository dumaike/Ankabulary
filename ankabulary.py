import requests
import json
import re


def remove_wrapper(input, wrapper_start, wrapper_end):
    result = input
    while wrapper_start in result:
        start_idx = result.index(wrapper_start)
        end_idx = result.index(wrapper_end, start_idx + len(wrapper_start))
        inner_word = result[start_idx + len(wrapper_start):end_idx]
        result = result[0:start_idx] + \
            inner_word + result[end_idx + len(wrapper_end):]

    return result


def remove_link_wrapper(input):
    return remove_wrapper(input, '{a_link|', '}')


def remove_synonym_wrapper(input):
    return remove_wrapper(input, '{sx|', '||}')


def remove_italics_wrapper(input):
    return remove_wrapper(input, '{it}', '{/it}')


api_key = '4996b4ec-219f-411e-9d36-403e40db7a7d'
word = 'voluminous'

url = f'https://www.dictionaryapi.com/api/v3/references/collegiate/json/{word}?key={api_key}'
response_obj = requests.post(url, json={})
response_txt = response_obj.text
response_dict = json.loads(response_txt[1:len(response_txt)-1])

one_definition = response_dict['def'][0]['sseq'][0][0][1]['dt'][0][1]
formatted_definition = one_definition.replace('{bc}', ': ')
formatted_definition = remove_synonym_wrapper(formatted_definition)
formatted_definition = remove_link_wrapper(formatted_definition)

part_of_speech = response_dict['fl']

all_ety = response_dict['et']
etymology = remove_italics_wrapper(response_dict['et'][0][1])

print(f'{part_of_speech} - {formatted_definition} - {etymology}')
