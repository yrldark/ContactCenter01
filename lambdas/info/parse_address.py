#
# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

import logging
import json

units = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6,
    'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12,
    'thirteen': 13, 'fourteen': 14, 'fifteen': 15, 'sixteen': 16, 'seventeen': 17,
    'eighteen': 18, 'nineteen': 19
}

tens = {
    'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60,
    'seventy': 70, 'eighty': 80, 'ninety': 90
}

scales = {
    'hundred': 100, 'thousand': 1000
}

ordinals = {
    'zeroth':      { 'unit': 'zero',      'suffix': 'th' },
    'first':       { 'unit': 'one',       'suffix': 'st' },
    'second':      { 'unit': 'two',       'suffix': 'nd' },
    'third':       { 'unit': 'three',     'suffix': 'rd' },
    'fourth':      { 'unit': 'four',      'suffix': 'th' },
    'fifth':       { 'unit': 'five',      'suffix': 'th' },
    'sixth':       { 'unit': 'six',       'suffix': 'th' },
    'seventh':     { 'unit': 'seven',     'suffix': 'th' },
    'eighth':      { 'unit': 'eight',     'suffix': 'th' },
    'nineth':      { 'unit': 'nine',      'suffix': 'th' },
    'tenth':       { 'unit': 'ten',       'suffix': 'th' },
    'eleventh':    { 'unit': 'eleven',    'suffix': 'th' },
    'twelveth':    { 'unit': 'twelve',    'suffix': 'th' },
    'thirteenth':  { 'unit': 'thirteen',  'suffix': 'th' },
    'fourteenth':  { 'unit': 'fourteen',  'suffix': 'th' },
    'fifteenth':   { 'unit': 'fifteen',   'suffix': 'th' },
    'sixteenth':   { 'unit': 'sixteen',   'suffix': 'th' },
    'seventeenth': { 'unit': 'seventeen', 'suffix': 'th' },
    'eighteenth':  { 'unit': 'eighteen',  'suffix': 'th' },
    'nineteenth':  { 'unit': 'nineteen',  'suffix': 'th' }
}

ordinal_endings = {
    'ieth': 'y', 'hundredth': 'hundred'
}

substitutions = {
    'oh': 'zero', 'o.': 'zero', 'dash': '-'
}

phrase_substitutions = {
    'and one half': '1/2', 'and a half': '1/2', ' and ': ' '
}

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def parse(address):
    current_number = 0  # latest number found in the address
    prior_number = 0    # prior number found in the address
    final_number = 0    # number being built; may be comprises of several number words

    ordinal_suffix = ''      
    output_address = ''

    # substitutions prior to the split
    for phrase in phrase_substitutions.keys():
        address = address.replace(phrase, phrase_substitutions[phrase])

    logger.debug('PROCESSING ADDRESS: {}'.format(address))
    words = address.split(' ')
 
    for position, word in enumerate(words):
        logger.debug('PROCESSING WORD: {}'.format(word))

        # subsitute "oh" for "zero", "dash" for "-", etc.
        if word in substitutions:
            word = substitutions[word]

        # take care of "fortieth", "fiftieth", "two hundredth", etc.
        for ending in ordinal_endings:
            if word.endswith(ending):
                logger.debug('it is an ordinal word: {}'.format(word))
                word = word.replace(ending, ordinal_endings[ending])
                ordinal_suffix = 'th'

        def log_vals(id):
            logger.debug('{}: current_number={}, prior_number={}, final_number={}'.format(
                     id, current_number, prior_number, final_number))

        if word in units or word in ordinals:
           words[position] = {'word': word, 'type': 'UNIT'}

           if word in ordinals:
               logger.debug('- 1 UNIT: it is an ordinal word: {}'.format(word))
               ordinal_suffix = ordinals[word]['suffix']
               words[position]['suffix'] = ordinal_suffix
               logger.debug('- 2 UNIT: ordinal_suffix = {}'.format(ordinal_suffix))
               word = ordinals[word]['unit']

           number = units[word]

           if position > 0 and words[position-1]['type'] == 'UNIT':
               final_number += current_number
               current_number = number
               log_vals('- 3 UNIT')
               logger.debug('- 4 UNIT: prior_word_is UNIT so capturing number')
               output_address += str(final_number) 
               logger.debug('- 5 UNIT: output_address = {}'.format(output_address))
               final_number = 0
           else:
               current_number += number
               log_vals('- 6 UNIT')

        elif word in tens:
           words[position] = {'word': word, 'type': 'TENS'}
           if ordinal_suffix:
               words[position]['suffix'] = ordinal_suffix
           number = tens[word]

           if position > 0:
               if words[position-1]['type'] in ['UNIT', 'TENS']:
                   logger.debug('- 1 TENS: prior_word_is {} so capturing number'.format(words[position-1]['type']))
                   output_address += str(final_number + current_number)
                   logger.debug('- 2 TENS: output_address = {}'.format(output_address))
                   final_number = 0
                   prior_number = current_number
                   current_number = 0

           current_number += number
           log_vals('- 5 TENS')

        elif word in scales:
           words[position] = {'word': word, 'type': 'SCALES'}
           if ordinal_suffix:
               words[position]['suffix'] = ordinal_suffix
           scale = scales[word]

           log_vals('- 1 SCALES')
           
           if ordinal_suffix != '':
               if current_number > 9:
                   current_number = current_number % 10 
                   logger.debug('- 2 SCALES: backing up a step and capturing number')
                   output_address += str(prior_number) 
                   logger.debug('- 3 SCALES: output_address = {}'.format(output_address))
               elif prior_number > 9 and final_number > 0:
                   logger.debug('- 4 SCALES: backing up a step and capturing number')
                   output_address += str(final_number) 
                   logger.debug('- 5 SCALES: output_address = {}'.format(output_address))
                   final_number = 0

           logger.debug('- 6 SCALES: {} * {} = {}'.format(current_number, scale, current_number * scale))
           final_number += current_number * scale
           prior_number = current_number
           current_number = 0
           log_vals('- 7 SCALES')

        else:
           words[position] = {'word': word, 'type': 'WORD'}
           if current_number > 0:
               final_number += current_number
           log_vals('- 1 WORD')

           if final_number > 0 or (position > 0 and words[position-1]['word'] == 'zero'):
               if position > 1:
                   if words[position-1]['type'] in ['UNIT', 'TENS', 'SCALES']:
                       if words[position-2]['type'] in ['UNIT', 'TENS']:
                           if ordinal_suffix != '':
                               logger.debug('- 2 WORD: prior two words are numbers, adding a space')
                               output_address += ' '
               logger.debug('- 3 WORD: final_number > 0, so capturing final_number + ordinal_suffix + SPACE')
               output_address += str(final_number) + ordinal_suffix + ' '
               logger.debug('- 4 WORD: output_address = {}'.format(output_address))
               ordinal_suffix = ''

           logger.debug('- 5 WORD: capturing SPACE + word + SPACE')
           output_address += ' ' + word + ' '
           logger.debug('- 6 WORD: output_address = {}'.format(output_address))

           prior_number = current_number
           final_number = current_number = 0


    logger.debug('')
    logger.debug('PROCESSING: <end>')
    log_vals('- 1 END')
    if current_number > 0 or word == 'zero':
        output_address += str(current_number) + ordinal_suffix
        logger.debug('- 2 END: output_address = {}'.format(output_address))
        ordinal_suffix = ''

    while '  ' in output_address:
        output_address = output_address.replace('  ', ' ')
    output_address = output_address.replace(' - ', '-')
    output_address = output_address.replace('.', '')
    output_address = output_address.strip()

    logger.debug('word array = \n{}'.format(json.dumps(words, indent=4)))

    return output_address


test_cases = [
    { 'input': 'twenty two thousand four hundred seventeen thirty second avenue south apartment three thirty three b. seattle washington nine eight one seven eight dash two two four nine',
      'expected': '22417 32nd avenue south apartment 333 b seattle washington 98178-2249'
    },
    { 'input': 'two forty two thirty second avenue south apartment three thirty three b. seattle washington nine eight one seven eight dash two two four nine',
      'expected': '242 32nd avenue south apartment 333 b seattle washington 98178-2249'
    },
    { 'input': 'it is twenty twenty two two hundredth avenue apartment three oh one dash three oh four b. omaha nebraska three four five six seven please and thank you',
      'expected': 'it is 2022 200th avenue apartment 301-304 b omaha nebraska 34567 please thank you'
    },
    { 'input': 'it is twenty twenty two hundredth avenue apartment three oh one dash three oh four b. omaha nebraska three four five six seven please and thank you',
      'expected': 'it is 2020 200th avenue apartment 301-304 b omaha nebraska 34567 please thank you'
    },
    { 'input': 'it is twenty two hundred two hundredth avenue apartment three oh one dash three oh four b. omaha nebraska three four five six seven please and thank you',
      'expected': 'it is 2200 200th avenue apartment 301-304 b omaha nebraska 34567 please thank you'
    },
    { 'input': 'it is twenty twenty two fortieth avenue apartment three oh one dash three oh four b. omaha nebraska three four five six seven please and thank you',
      'expected': 'it is 2022 40th avenue apartment 301-304 b omaha nebraska 34567 please thank you'
    },
    { 'input': 'it is twenty twenty two fifty seventh avenue apartment three oh one dash three oh four b. omaha nebraska three four five six seven please and thank you',
      'expected': 'it is 2022 57th avenue apartment 301-304 b omaha nebraska 34567 please thank you'
    },
    { 'input': 'it is twenty twenty fifty seventh avenue apartment three oh one dash three oh four b. omaha nebraska three four five six seven please and thank you',
      'expected': 'it is 2020 57th avenue apartment 301-304 b omaha nebraska 34567 please thank you'
    },
    { 'input': 'it is twenty twenty two one hundred fifty seventh avenue apartment three oh one dash three oh four b. omaha nebraska three four five six seven please and thank you',
      'expected': 'it is 2022 157th avenue apartment 301-304 b omaha nebraska 34567 please thank you'
    },
    { 'input': 'it is twenty twenty two one hundred and fifty seventh avenue apartment three oh one dash three oh four b. omaha nebraska three four five six seven please and thank you',
      'expected': 'it is 2022 157th avenue apartment 301-304 b omaha nebraska 34567 please thank you',
    },
    { 'input': 'it is twenty twenty two seventh avenue apartment three oh one dash three oh four b. omaha nebraska three four five six seven please and thank you',
      'expected': 'it is 2022 7th avenue apartment 301-304 b omaha nebraska 34567 please thank you',
    },
    { 'input': 'seventy four seventh avenue apartment three oh one dash three oh four b. omaha nebraska three four five six seven',
      'expected': '74 7th avenue apartment 301-304 b omaha nebraska 34567',
    },
    { 'input': 'four twenty five and one half hill street santa monica california nine oh four oh five',
      'expected': '425 1/2 hill street santa monica california 90405'
    },
    { 'input': 'four twenty five and a half hill street santa monica california nine oh four oh five',
      'expected': '425 1/2 hill street santa monica california 90405'
    },
    { 'input': 'it is twenty twenty fortieth avenue apartment three oh one dash three oh four b. omaha nebraska three four five six seven dash four oh four seven please and thank you',
      'expected': 'it is 2020 40th avenue apartment 301-304 b omaha nebraska 34567-4047 please thank you'
    },
    { 'input': 'twenty four eighty northwest twenty third street miami florida three three one four two',
      'expected': '2480 northwest 23rd street miami florida 33142'
    },
    { 'input': 'three one two randolph street dakota iowa five one oh three oh',
      'expected': '312 randolph street dakota iowa 51030'
    },
    { 'input': 'three one oh randolph street dakota iowa five one oh three oh',
      'expected': '310 randolph street dakota iowa 51030'
    }
]

def parse_tests():
    for index, test in enumerate(test_cases):
        result = parse_address(test['input'])
        if result != test['expected']:
            logger.debug('TEST #{:03d} - ERROR: {}'.format(index, result))
        else:
            logger.debug('TEST #{:03d} - SUCCESS: {}'.format(index, result))


