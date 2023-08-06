import requests
import json

# ****************************************************************************#
#                                 GLOBAL                                      #
# ****************************************************************************#

# Configuration
api_key = '4996b4ec-219f-411e-9d36-403e40db7a7d'
input_file_name = 'raw_word_list.txt'
output_file_name = 'generated_anki_cards.txt'
space_char = '&nbsp;'

# Global logging variables
total_processed_words = 0
total_not_found_words = 0
not_found_words_list = []
total_skipped_words = 0
skipped_words_list = []


class ProcessedWord:
    def __init__(self):
        self.word = ""
        self.definition = ""
        self.etymology = ""
        self.part_of_speech = ""


def main():
    global total_not_found_words
    global total_processed_words
    global not_found_words_list

    print('Connecting to Merriam-Webster.')
    words = fetch_definitions_from_file()
    write_anki_file(words)

    print('Ankabulary execution complete! ')
    print('*****************************************************************')
    print(f'{total_processed_words} words processed and written to {output_file_name}')
    if total_not_found_words > 0:
        print(
            f'Definitions for {total_not_found_words} words not found - {not_found_words_list}')
    if total_skipped_words > 0:
        print(f'{total_skipped_words} duplicate words skipped - {skipped_words_list}')
    print('Never forget that you are loved <3')


# ****************************************************************************#
#                       FETCHING AND RESPONSE READING                         #
# ****************************************************************************#

def fetch_definitions_from_file():
    global total_skipped_words
    global skipped_words_list

    try:
        input_file = open(input_file_name, "r")
    except Exception as e:
        print(
            f'Error: Input file named "{input_file_name}" not found. Aborting!')
        return []

    input_file_contents = input_file.read()
    words = input_file_contents.split('\n')
    processed_words = {}
    for word in words:
        # If this exact word already exists in the results, skip it.
        if word.lower() in processed_words:
            total_skipped_words = total_skipped_words + 1
            skipped_words_list.append(word)
            continue

        proccessed_result = fetch_single_word(word)

        # If no definition was found, skip it.
        if proccessed_result is None:
            continue

        # If a conjugation of this word is already in the results, skip it.
        if proccessed_result.word in processed_words:
            total_skipped_words = total_skipped_words + 1
            continue

        processed_words[proccessed_result.word] = proccessed_result
    return processed_words


# Returns None if the word wasn't found
def fetch_single_word(word):
    global total_not_found_words
    global not_found_words_list

    processed_word = ProcessedWord()

    url = f'https://www.dictionaryapi.com/api/v3/references/collegiate/json/{word}?key={api_key}'
    response_obj = requests.post(url, json={})
    response_txt = response_obj.text
    response_dict = None
    try:
        response_array = json.loads(response_txt)

        # Only take the first part of speech to proccess
        response_dict = response_array[0]
        processed_word.definition = read_definitions_from_response(
            response_dict, word)
    except Exception as e:
        print(
            f'Error: when looking up word "{word}". Skipping Word. The word '
            'could be missing or there could have been an unexpected formatting '
            'in the response.')
        total_not_found_words = total_not_found_words + 1
        not_found_words_list.append(word)
        return None

    processed_word.part_of_speech = clean_webster_formatting(
        response_dict['fl'])

    try:
        processed_word.etymology = clean_webster_formatting(
            response_dict['et'][0][1])
    except Exception as e:
        print(
            f'Info: Word "{word}" has no etymology.')

    processed_word.word = clean_word_id(response_dict['meta']['id'])

    return processed_word


def read_definitions_from_response(response_dict, word):
    return_definition = ''
    definitions = response_dict['def']

    definition_index = 1
    for sub_def in definitions:
        sense_sequence = sub_def['sseq']
        for sub_sseq in sense_sequence:
            for sub_sseq2 in sub_sseq:
                if 'sn' in sub_sseq2[1]:
                    parsed_definition = read_single_sense(
                        definition_index, sub_sseq2)
                    if parsed_definition is not None:
                        definition_index = definition_index + 1
                        return_definition = return_definition + \
                            parsed_definition
                elif sub_sseq2[0] == 'pseq':
                    for pseq in sub_sseq2[1]:
                        parsed_definition = read_single_sense(
                            definition_index, pseq)
                        if parsed_definition is not None:
                            definition_index = definition_index + 1
                            return_definition = return_definition + \
                                parsed_definition
                elif 'dt' in sub_sseq2[1]:
                    # This word only has a single definition, so just grab it.
                    return clean_webster_formatting(sub_sseq2[1]['dt'][0][1])
                else:
                    print(f'Error: The API Response for {word} had unexpected '
                          'formatting. Double check the card output.')

    return return_definition.strip()


def read_single_sense(index, sense):
    sense_text = sense[1]

    # TODO: Support variant entries.
    if ('vrs' in sense_text and 'dt' not in sense_text):
        return None

    # TODO: Support inflection entries.
    if ('ins' in sense_text and 'dt' not in sense_text):
        return None

    raw_definition = clean_webster_formatting(sense_text['dt'][0][1])
    definition = str(index) + ') ' + raw_definition + '<br>'

    return definition


# ****************************************************************************#
#                              OUTPUT GENERATION                              #
# ****************************************************************************#

def write_anki_file(words):
    # Exit early if there are no words to avoid false logging.
    if (len(words) == 0):
        return

    output_file = open(output_file_name, "w", encoding="utf-8")

    # Write the header Anki expects on import.
    output_file.write('#separator:tab\n')
    output_file.write('#html:true\n')
    output_file.write('#tags column:11\n')

    for word in words.values():
        write_word(word, output_file)

    output_file.close()


def write_word(word: ProcessedWord, file):
    global total_processed_words

    file.write(word.word + "\t")
    file.write(word.definition + "\t\t\t\t\t")
    file.write(word.part_of_speech + "\t\t\t")
    file.write(word.etymology + "\n")
    total_processed_words = total_processed_words + 1


# ****************************************************************************#
#                              STRING FORMATTING                              #
# ****************************************************************************#

# The Webster formatting has a lot of custom markup that we need to strip,
# convert to html, or change to special characters.
def clean_webster_formatting(input):
    result = input
    result = replace_colons(input)
    result = remove_synonym_wrappers(result)
    result = remove_auto_link_wrappers(result)
    result = remove_direct_link_wrappers(result)
    result = remove_etymology_link_wrappers(result)
    result = remove_directional_wrappers(result)
    result = remove_directional_etymology_chunk(result)
    result = remove_more_at_chunk(result)
    result = replace_italics_wrappers(result)
    result = remove_cross_reference_chunk(result)
    return result


# Removes the beginning and end sections of a wrapper, but leaves the wrapped
# contents.
def remove_wrapper(input, wrapper_start, wrapper_end):
    result = input
    start_idx = result.index(wrapper_start)
    end_idx = result.index(wrapper_end, start_idx + len(wrapper_start))
    inner_word = clean_word_id(result[start_idx + len(wrapper_start):end_idx])
    result = result[0:start_idx] + \
        inner_word + result[end_idx + len(wrapper_end):]

    return result


def remove_double_piped_wrappers(input, pipe_start):
    pipe_start = '{' + pipe_start + '|'
    while pipe_start in input:
        chunk_start_idx = input.index(
            pipe_start) + len(pipe_start)
        wrapper_end = copy_wrapped_chunk(input[chunk_start_idx:], '|', '}')
        input = remove_wrapper(input, pipe_start, wrapper_end)

    return input


# A chunk is an entire wrapped section, including the inner contents.
def copy_wrapped_chunk(input, chunk_start, chunk_end):
    chunk_start_idx = 0
    chunk_end_idx = 0
    if chunk_start not in input:
        print(f'Error: Could not find wrapper_start \
              ({chunk_start}) in string ({input})')
    else:
        chunk_start_idx = input.index(chunk_start)

    # Just the substring from the chunk start to the end of the full input.
    partial_chunk = input[chunk_start_idx + len(chunk_start):]
    if chunk_end not in partial_chunk:
        print(f'Error: Could not find wrapper_end \
              ({chunk_end}) in string ({input}) after {chunk_start}')
    else:
        chunk_end_idx = partial_chunk.index(chunk_end)

    return chunk_start + partial_chunk[: chunk_end_idx + len(chunk_end)]


def remove_auto_link_wrappers(input):
    auto_link_start = '{a_link|'
    while auto_link_start in input:
        input = remove_wrapper(input, auto_link_start, '}')
    return input


def remove_direct_link_wrappers(input):
    return remove_double_piped_wrappers(input, 'd_link')


def remove_etymology_link_wrappers(input):
    return remove_double_piped_wrappers(input, 'et_link')


def remove_synonym_wrappers(input):
    return remove_double_piped_wrappers(input, 'sx')


def remove_directional_wrappers(input):
    outer_wrapper_start = '{dx}'
    outer_wrapper_end = '{/dx}'
    inner_wrapper_start = '{dxt|'
    while outer_wrapper_start in input:
        original_outer_chunk = copy_wrapped_chunk(
            input, outer_wrapper_start, outer_wrapper_end)
        inner_chunk = copy_wrapped_chunk(
            original_outer_chunk, inner_wrapper_start, '}')
        inner_wrapper_end = copy_wrapped_chunk(
            inner_chunk[len(inner_wrapper_start):], '|', '}')
        outer_chunk_with_unwrapped_inner_word = remove_wrapper(
            original_outer_chunk, inner_wrapper_start, inner_wrapper_end)
        unwrapped_outer_chunk = remove_wrapper(
            outer_chunk_with_unwrapped_inner_word, outer_wrapper_start, outer_wrapper_end)
        input = input.replace(original_outer_chunk,
                              '; ' + unwrapped_outer_chunk)
    return input


def remove_more_at_chunk(input):
    more_at_start = '{ma}'
    while more_at_start in input:
        chunk = copy_wrapped_chunk(input, more_at_start, '{/ma}')
        input = input.replace(chunk, '')
    return input


def remove_directional_etymology_chunk(input):
    wrapper_start = '{dx_ety}'
    while wrapper_start in input:
        chunk = copy_wrapped_chunk(input, wrapper_start, '{/dx_ety}')
        input = input.replace(chunk, '')
    return input


def remove_cross_reference_chunk(input):
    wrapper_start = '{dx_def}'
    while wrapper_start in input:
        chunk = copy_wrapped_chunk(input, wrapper_start, '{/dx_def}')
        input = input.replace(chunk, '')
    return input


# Word IDs where there are mulitple words have a colon followed by the index
# of this particular definition. We take the first definition, so this isn't
# needed.
def clean_word_id(input):
    multi_entry_delimiter = ":"
    if multi_entry_delimiter in input:
        input = input[:input.index(multi_entry_delimiter)]
    return input


def replace_colons(input):
    colon_str = '{bc}'
    # Each definition has a leading colon, which doesn't suit Ank formatting
    if colon_str in input and input.index(colon_str) == 0:
        input = input[4:]

    # Replace the remaining colons.
    return input.replace(colon_str, '<b>:</b> ')


def replace_italics_wrappers(input):
    input = input.replace('{it}', '<em>')
    input = input.replace('{/it}', '</em>')
    return input


def n_spaces(n):
    spaces = ''
    for idx in range(n):
        spaces = spaces + space_char
    return spaces


main()
