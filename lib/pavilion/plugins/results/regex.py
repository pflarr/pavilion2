from pavilion import result_parsers
import yaml_config as yc
import re


class Regex(result_parsers.ResultParser):
    """Find matches to the given regex in the given file. The matched string
    or strings are returned as the result."""

    def __init__(self):
        super().__init__(name='regex')
        self.range_re = re.compile('(-?[0-9]*\.?[0-9]*)-(-?.*)')

    def get_config_items(self):

        config_items = super().get_config_items()
        config_items.extend([
            yc.StrElem(
                'regex', required=True,
                help_text="The python regex to use to search the given file. "
                          "See: 'https://docs.python.org/3/library/re.html' "
                          "You can use single quotes in YAML to have the "
                          "string interpreted literally. IE '\\n' is a '\\' "
                          "and an 'n'."
            ),
            # Use the built-in matches element.
            result_parsers.MATCHES_ELEM,
            yc.StrElem(
                'threshold', default=None,
                help_text="If a threshold is defined, 'pass' will be returned "
                          "if greater than or equal to that many instances "
                          "of the specified word are found.  If fewer "
                          "instances are found, 'fail' is returned.  If no "
                          "threshold is defined, the count will be returned."
            ),
            yc.ListElem(
                'expected', sub_elem=yc.StrElem(),
                help_text="Optional expected value(s) and/or range(s).  If "
                          "provided, the result will be 'PASS' if all of the "
                          "found values (determined by the 'results' value) "
                          "are within the expected range(s) or value(s).  "
                          "Otherwise, the result is 'FAIL'. Supports "
                          "integers and floats."
            )
        ])

        return config_items

    def _check_args(self, regex=None, match_type=None, threshold=None,
            expected=None):

        try:
            re.compile(regex)
        except ValueError as err:
            raise result_parsers.ResultParserError(
                "Invalid regular expression: {}".format(err))

        if not isinstance(expected, list):
            raise result_parsers.ResultParserError(
                "Expected should be a list.")

        for item in expected:
            test_list = []

            if '-' in item[1:]:
                test_list = list(self.range_re.search(item).groups())
                # Check for valid second part of range.
                if '-' in test_list[1][1:]:
                    raise result_parsers.ResultParserError(
                        "Invalid range: {}".format(item)
                    )
            else:
                test_list = [ item ]

            for test_item in test_list:
                # Check for values as integers.
                try:
                    float(test_item)
                except ValueError as err:
                    raise result_parsers.ResultParserError(
                        "Invalid value: {}".format(test_item)
                    )

            if len(test_list) > 1:
                # Check for range specification as
                # (<lesser value>-<greater value>)
                if float(test_list[1]) < float(test_list[0]):
                    raise result_parsers.ResultParserError(
                        "Invalid range: {}".format(item))

    def __call__(self, test, file, regex=None, match_type=None, threshold=None,
            expected=None):

        regex = re.compile(regex)

        matches = []

        for line in file.readlines():
            match = regex.search(line)

            if match is not None:
                matches.append(match.group())

        # Test if the number of matches meets the specified threshold
        if threshold is not None:
            return (len(matches) >= threshold)
        # Test if the found values are within any of the specified expected
        # ranges.
        elif expected is not None:
            # Initially set to false for all matches.
            ret_vals = [False for x in range(0,len(matches))]
            for i in range(0,len(ret_vals)):
                for j in range(0,len(expected)):
                    # Not a range, checking for exact match.
                    if '-' not in expected[j][1:] and \
                            float(matches[i]) == float(expected[j]):
                                ret_vals[i] = True
                    # Checking if found value is in this range.
                    elif '-' in expected[j][1:]:
                        low, high = self.range_re.search(expected[j]).groups()
                        if float(low) <= float(matches[i]) <= float(high):
                            ret_vals[i] = True
            return ret_vals
        elif match_type == result_parsers.MATCH_FIRST:
            return matches[0] if matches else None
        elif match_type == result_parsers.MATCH_LAST:
            return matches[-1] if matches else None
        elif match_type == result_parsers.MATCH_ALL:
            return matches
        else:
            raise result_parsers.ResultParserError(
                "Invalid 'matches' value '{}'".format('matches')
            )
