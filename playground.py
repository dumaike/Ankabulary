import requests
import json
import re


def remove_wrapper(input, wrapper_start, wrapper_end):
    result = input
    while wrapper_start in result:
        start_idx = input.index(wrapper_start)
        end_idx = input.index(wrapper_end, start_idx + len(wrapper_start))
        inner_word = input[start_idx + len(wrapper_start):end_idx]
        result = input[0:start_idx] + \
            inner_word + input[end_idx + len(wrapper_end):]

    return result


def remove_italics_wrapper(input):
    return remove_wrapper(input, '{it}', '{/it}')


input = "Late Latin {it}voluminosus{/it}, from Latin {it}volumin-, volumen{/it}"
input = remove_italics_wrapper(input)

print(f'{input}')
