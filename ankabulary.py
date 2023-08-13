import requests
import json
from enum import Enum

# **************************************************************************#
# This script looks for a txt file called 'generated_anki_cards.txt'. The   #
# should be a list of words separated by newlines. For each word, it will   #
# query Merriam-Webster's API and process the results into an object. Those #
# will then be written to a file called 'raw_word_list.txt' in a file       #
# format that can be imported into Anki.                                    #
#                                                                           #
# Normally I wouldn't create one large Python file, but for portability     #
# I decided to structure it this way.                                       #
# **************************************************************************#

# **************************************************************************#
#                                 GLOBAL                                    #
# **************************************************************************#

# Configuration settings.
input_file_name = 'raw_word_list.txt'
output_file_name = 'generated_anki_cards.txt'
space_char = '&nbsp;'
line_break = '<br>'
split_token = ', '

# A dictionary of log resuts of word fetching.
processed_words_results_dict = {}


# The final results types for each word being fetched (for logging).
class LogType(Enum):
    PROCESSED = 1
    ERROR = 2
    DUPLICATE = 3
    VARIANT = 4
    INFLECTION = 5
    MISSING_ETYMOLOGY = 6
    MISSING_POS = 7

# A word that has been fetched from a dictionary API and flattened into
# simple plaintext fields for Anki.
class ProcessedWord:
    def __init__(self):
        self.word = ""
        self.merged_definitions = ""
        self.etymology = ""
        self.part_of_speech = ""

        
# On object returned when one definition is parsed.
class ProcessedDefinition:
    def __init__(self):
        self.next_index = 0 # The index of the next processed result.
        self.definition_entry = ""

# ****************************************************************************#
#                                 MAIN                                        #
# ****************************************************************************#


def main():
    init_logs()

    print('*****************************************************************')
    print('Connecting to Merriam-Webster.')    
    print('Fetching word results.')
    words = fetch_definitions_from_file()
    write_anki_file(words)

    print('*****************************************************************')
    print('Ankabulary execution complete! \n')

    print_processed_word_result(LogType.ERROR, "had errors. No card's weren't created for them.")
    print_processed_word_result(LogType.MISSING_ETYMOLOGY, "were missing etymologies.")
    print_processed_word_result(LogType.MISSING_POS, "were missing parts of speech.")
    print_processed_word_result(LogType.DUPLICATE, "were duplicates of other words in the list, and cards were'nt created for them.")
    print_processed_word_result(LogType.VARIANT, "had variant data that wasn't processed")
    print_processed_word_result(LogType.INFLECTION, "had inflection data that wasn't processed")
    print_processed_word_result(LogType.PROCESSED, "were fully processed!")

    print('Never forget that you are loved <3')
    
    print('*****************************************************************')


# ****************************************************************************#
#                       FETCHING AND RESPONSE READING                         #
# ****************************************************************************#

def fetch_definitions_from_file():

    try:
        input_file = open(input_file_name, "r", encoding="utf-8")
    except Exception as e:
        print(
            f'Error: Input file named "{input_file_name}" not found. Aborting!')
        return []

    input_file_contents = input_file.read()
    words = input_file_contents.split('\n')
    processed_words = {}
    for word in words:
        # Ignore empty lines.
        if len(word.strip()) == 0:
            continue 

        # If this exact word already exists in the results, skip it.
        if word.lower() in processed_words:
            log_word_result(LogType.DUPLICATE, word)
            continue

        proccessed_result = fetch_single_word(word)

        # If no definition was found, skip it.
        if proccessed_result is None:
            continue

        # If a conjugation of this word is already in the results, skip it.
        if proccessed_result.word in processed_words:
            log_word_result(LogType.DUPLICATE, word)
            continue

        processed_words[proccessed_result.word] = proccessed_result
    return processed_words


# Fetches a single word definition, flattens it into a ProcessedWord and returns
# that. Returns None if the word wasn't found
def fetch_single_word(word):
    api_key = '4996b4ec-219f-411e-9d36-403e40db7a7d'
    url = f'https://www.dictionaryapi.com/api/v3/references/collegiate/json/{word}?key={api_key}'

    response_obj = requests.post(url, json={})
    response_txt = response_obj.text
    response_dict = None

    processed_word = ProcessedWord()
    try:
        response_array = json.loads(response_txt)

        # Only take the first part of speech to proccess
        response_dict = response_array[0]
        processed_word.merged_definitions = read_definitions_from_response(
            response_dict, word)
    except Exception as e:
        log_word_result(LogType.ERROR, word)
        return None

    try:
        processed_word.part_of_speech = clean_webster_formatting(
        response_dict['fl'])
    except Exception as e:
        log_word_result(LogType.MISSING_POS, word)    

    try:
        processed_word.etymology = clean_webster_formatting(
            response_dict['et'][0][1])
    except Exception as e:
        log_word_result(LogType.MISSING_ETYMOLOGY, word)

    processed_word.word = clean_word_id(response_dict['meta']['id'])

    return processed_word


def read_definitions_from_response(response_dict, word):
    if 'def' in response_dict:
        return read_standard_definition(response_dict['def'], word)
    
    if 'cxs' in response_dict:
        return read_cognate_cross_reference(response_dict['cxs'], word)
    
    raise Exception('Response contains neither a "def" or "cxs" object')

def read_standard_definition(def_dict, word):
    return_definition = ''

    definition_index = 1
    for def_entry in def_dict:
        if 'sls' in def_entry:
            parsed_definition = read_definition_leaf(
                        definition_index, def_entry,  word)
            definition_index = parsed_definition.next_index
            return_definition = return_definition + \
                parsed_definition.definition_entry

        sense_sequence = def_entry['sseq']
        for sub_sseq in sense_sequence:
            for sub_sseq2 in sub_sseq:
                if 'sn' in sub_sseq2[1]:

                    parsed_definition = read_definition_leaf(
                        definition_index, sub_sseq2[1],  word)
                    definition_index = parsed_definition.next_index
                    return_definition = return_definition + \
                        parsed_definition.definition_entry
                        
                elif sub_sseq2[0] == 'pseq':

                    for pseq in sub_sseq2[1]:
                        parsed_definition = read_definition_leaf(
                            definition_index, pseq[1], word)
                        definition_index = parsed_definition.next_index
                        return_definition = return_definition + \
                            parsed_definition.definition_entry
                            
                elif 'dt' in sub_sseq2[1]:
                    leaf_entry = sub_sseq2[1]['dt']
                    # TODO: Usage notes are equilavent to a definition,
                    # so unwrap them.
                    if 'uns' in leaf_entry[0]:
                        leaf_entry = leaf_entry[0][1][0]
                    
                    # This is a standalone definition (plus a possible label),
                    # so just return it.
                    return return_definition + \
                        clean_webster_formatting(leaf_entry[0][1])                    
                else:
                    print(f'Info: The API Response for {word} had unexpected '
                          'formatting, but no errors were thrown. Double '
                          'check the card output.')

    return return_definition.strip()

def read_cognate_cross_reference(cxs_dict, word):
    return_definition = ''

    for cxs_entry in cxs_dict:
        return_definition = return_definition + cxs_entry['cxl'] + space_char
        # The cxs label will contain cross reference targets.
        for cxtis_entry in cxs_entry['cxtis']:
            return_definition = \
                return_definition + cxtis_entry['cxt'] + split_token

    # Strip the trailing ", " from the cxt label list.
    return_definition = \
        strip_trailing_split_token(return_definition) + line_break

    return return_definition.strip()

def read_definition_leaf(index, sense_text, word):
    return_result = ProcessedDefinition()
    return_result.next_index = index
    return_result.definition_entry = ''

    # TODO: Support variant entries.
    if 'vrs' in sense_text and 'dt' not in sense_text:
        log_word_result(LogType.VARIANT, word)
        return return_result

    # TODO: Support inflection entries.
    if 'ins' in sense_text and 'dt' not in sense_text:        
        log_word_result(LogType.INFLECTION, word)
        return return_result
        
    # This entry is a label for future sub-entries, not a definition.
    if 'sls' in sense_text and 'dt' not in sense_text:
        label_list = ''
        for label_entry in sense_text['sls']:
            label_list = label_list + label_entry + split_token

        return_result.definition_entry = \
            label_wrapper(strip_trailing_split_token(label_list) + line_break)
        return return_result

    # It's a definition.
    raw_definition = clean_webster_formatting(sense_text['dt'][0][1])
    return_result.definition_entry = \
        str(index) + ') ' + raw_definition + line_break
    return_result.next_index = return_result.next_index + 1

    return return_result


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
    file.write(word.word + "\t")
    file.write(word.merged_definitions + "\t\t\t\t\t")
    file.write(word.part_of_speech + "\t\t\t")
    file.write(word.etymology + "\n")
    log_word_result(LogType.PROCESSED, word.word)


# ****************************************************************************#
#                              STRING FORMATTING                              #
# ****************************************************************************#

# The Webster formatting has a lot of custom markup that we need to strip,
# convert to html, or change to special characters.
def clean_webster_formatting(input):
    # TODO: See if you can turn some of these links into hyperlinks that 
    # Anki could process instead of stripping them.
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
            outer_chunk_with_unwrapped_inner_word, \
            outer_wrapper_start, outer_wrapper_end)
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
    # Each definition has a leading colon, which doesn't suit Ank formatting.
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

def strip_trailing_split_token(input):
    return input[:len(input) - len (split_token)]

def label_wrapper(input):
    returned_text = '<span style="color: #b8b8b8"><b>' + input.upper() + '</b></span>'
    return returned_text


# ****************************************************************************#
#                              LOGGING                                        #
# ****************************************************************************#

def init_logs():
    global processed_words_results_dict
    for log_type in LogType:
        processed_words_results_dict[log_type] = []

def log_word_result(log_type: LogType, word):
    global processed_words_results_dict

    processed_words_results_dict[log_type].append(word)

def print_processed_word_result(log_type: LogType, description):    
    global processed_words_results_dict

    words_list = processed_words_results_dict[log_type]
    if len(words_list) > 0:
        print(
            f'{len(words_list)} word(s) {description} - {words_list} \n\n')



main()
