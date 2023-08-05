import requests
import json

api_key = '4996b4ec-219f-411e-9d36-403e40db7a7d'
input_file_name = 'word_list.txt'
output_file_name = 'anki_cards.txt'


class ProcessedWord:
    def __init__(self):
        self.word = ""
        self.definition = ""
        self.etymology = ""
        self.part_of_speech = ""


def main():
    words = fetch_definitions_from_file()
    write_anki_file(words)
    print("Ankabulary execution complete!")


def fetch_definitions_from_file():
    try:
        input_file = open(input_file_name, "r")
    except Exception as e:
        print(
            f'Error: Input file named "{input_file_name}" not found. Aborting!')
        return []

    input_file_contents = input_file.read()
    words = input_file_contents.split()
    processed_words = []
    for word in words:
        proccessed_result = fetch_single_word(word)
        if (proccessed_result is not None):
            processed_words.append(proccessed_result)
    return processed_words


def fetch_single_word(word):
    processed_word = ProcessedWord()

    url = f'https://www.dictionaryapi.com/api/v3/references/collegiate/json/{word}?key={api_key}'
    response_obj = requests.post(url, json={})
    response_txt = response_obj.text
    response_dict = None
    try:
        response_array = json.loads(response_txt)
        response_dict = response_array[0]
    except Exception as e:
        print(
            f'Error when looking up word "{word}" in Merriam-Webster. \n'
            f'Response: {response_txt}. \nSkipping Word.')
        return response_dict

    top_definition = response_dict['def'][0]['sseq'][0][0][1]['dt'][0][1]
    processed_word.definition = clean_webster_formatting(top_definition)
    processed_word.part_of_speech = clean_webster_formatting(
        response_dict['fl'])

    try:
        processed_word.etymology = clean_webster_formatting(
            response_dict['et'][0][1])
    except Exception as e:
        print(
            f'Info: Word "{word}" has no etymology in Merriam-Webster.')

    multi_entry_delimiter = ":"
    word_id = response_dict['meta']['id']
    if multi_entry_delimiter in word_id:
        word_id = word_id[:word_id.index(multi_entry_delimiter)]
    processed_word.word = word_id

    return processed_word


def write_anki_file(words):
    # Exit early if there are no words to avoid false logging.
    if (len(words) == 0):
        return

    output_file = open(output_file_name, "w", encoding="utf-8")

    # Write the header
    output_file.write('#separator:tab\n')
    output_file.write('#html:true\n')
    output_file.write('#tags column:11\n')

    for word in words:
        write_word(word, output_file)

    output_file.close()
    print(f'Processed words written to {output_file_name}')


def write_word(word: ProcessedWord, file):
    file.write(word.word + "\t")
    file.write(word.definition + "\t\t\t\t\t")
    file.write(word.part_of_speech + "\t\t\t")
    file.write(word.etymology + "\n")


def clean_webster_formatting(input):
    result = input
    result = replace_colons(input)
    result = remove_synonym_wrappers(result)
    result = remove_auto_link_wrappers(result)
    result = remove_direct_link_wrappers(result)
    result = remove_italics_wrappers(result)
    result = remove_more_at_chunk(result)
    return result


# Removes the beginning and end sections of a wrapper, but leaves the wrapped
# contents
def remove_wrapper(input, wrapper_start, wrapper_end):
    result = input
    start_idx = result.index(wrapper_start)
    end_idx = result.index(wrapper_end, start_idx + len(wrapper_start))
    inner_word = result[start_idx + len(wrapper_start):end_idx]
    result = result[0:start_idx] + \
        inner_word + result[end_idx + len(wrapper_end):]

    return result


# A chunk is an entire wrapped section, including the inner contents.
def generate_wrapped_chunk(input, chunk_start, chunk_end):
    chunk_start_idx = 0
    chunk_end_idx = 0
    if chunk_start not in input:
        print(f'Error: Could not find wrapper_start \
              ({chunk_start}) in string ({input})')
    else:
        chunk_start_idx = input.index(chunk_start)

    if chunk_end not in input:
        print(f'Error: Could not find wrapper_end \
              ({chunk_end}) in string ({input})')
    else:
        chunk_end_idx = input.index(chunk_end)

    return input[chunk_start_idx: chunk_end_idx + len(chunk_end)]


def remove_auto_link_wrappers(input):
    auto_link_start = '{a_link|'
    while auto_link_start in input:
        input = remove_wrapper(input, auto_link_start, '}')
    return input


def remove_direct_link_wrappers(input):
    direct_link_start = '{d_link|'
    while direct_link_start in input:
        chunk_start_idx = input.index(
            direct_link_start) + len(direct_link_start)
        wrapper_end = generate_wrapped_chunk(input[chunk_start_idx:], '|', '}')
        input = remove_wrapper(input, direct_link_start, wrapper_end)

    return input


def remove_synonym_wrappers(input):
    synonym_start = '{sx|'
    while synonym_start in input:
        input = remove_wrapper(input, synonym_start, '||}')
    return input


def remove_italics_wrappers(input):
    italics_start = '{it}'
    while italics_start in input:
        input = remove_wrapper(input, italics_start, '{/it}')
    return input


def remove_more_at_chunk(input):
    more_at_start = '{ma}'
    while more_at_start in input:
        chunk = generate_wrapped_chunk(input, more_at_start, '{/ma}')
        input = input.replace(chunk, '')
    return input


def replace_colons(input):
    colon_str = '{bc}'
    if colon_str in input and input.index(colon_str) == 0:
        input = input[4:]
    return input.replace(colon_str, '; ')


main()
