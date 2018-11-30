import jellyfish._jellyfish as py_jellyfish

class DistanceDiscreteEvents:
    '''
    Take as input 2 lists, e.g., arr1 = ['a','b','c'].
    These 2 lists can be compared using the methods damerau or levensthein
    '''

    def __init__(self, arr1, arr2):
        if arr1 == []:
            arr1 = ['']
        if arr2 == []:
            arr2 = ['']
        self.arr1 = arr1
        self.arr2 = arr2

        self.str1 = self.convert_to_string(arr1)
        self.str2 = self.convert_to_string(arr2)

    def convert_to_string(self, list_char):
        string_to_return = ''
        for ch in list_char:
            if ch == 'end':
                string_to_return += 'e'
            elif ch == '':
                string_to_return += ' '
            else:
                string_to_return += chr(int(ch)+161)

        return string_to_return

    def damerau(self):
        return 1.0 - py_jellyfish.damerau_levenshtein_distance(self.str1, self.str2)  / max( len(self.str1), len(self.str2) )

    def levenshtein(self):
        return 1.0 - py_jellyfish.levenshtein_distance(self.str1, self.str2)  / max( len(self.str1), len(self.str2) )