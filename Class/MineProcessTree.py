from anytree import Node, PreOrderIter, LevelOrderIter, findall, RenderTree
import re


class MineProcessTree:
    def __init__(self, length, cluster_id, settings, xes_name):
        self.length = length
        self.cluster_id = cluster_id
        self.settings = settings
        self.xes_name = xes_name

    def parseTree(self):
        '''
        Read tree in string (e.g., "Seq(1,XorLoop(Seq(XorLoop(2,tau,tau),3,4),tau,tau))")
        :return: anytree
        '''
        file = open(self.settings['base_folder'] + 'xes_temp_output/'+ self.settings['folder_name'] + str(self.xes_name)+'.xes.txt', 'r')
        tree_text = file.read()
        tree_text = tree_text.replace(' ','')
        tree_text = tree_text.replace("\n",'')

        childs = self.nextLevel(tree_text)

        if len(childs)!=1:
            exit('Problem while parsing the process tree')

        if type(childs[0]) == tuple:
            operator_name = childs[0][0]
            childrens_to_parse = childs[0][1]
        else:
            operator_name = childs[0]
            childrens_to_parse = ""

        root = Node(operator_name, childrens_to_parse=childrens_to_parse)

        while True:
            nodes = [node for node in PreOrderIter(root, filter_=lambda n: n.childrens_to_parse != '')]
            if len(nodes)==0:
                break
            else:
                for node in nodes:
                    childs = self.nextLevel(node.childrens_to_parse)
                    for child in childs:
                        if child == None or child == '':
                            continue
                        elif type(child) == tuple:
                            operator_name = child[0]
                            childrens_to_parse = child[1]
                        else:
                            operator_name = child
                            childrens_to_parse = ""

                        node.childrens_to_parse=''
                        Node(operator_name, childrens_to_parse=childrens_to_parse, parent=node)

        # Remove attribute childrens_to_parse not needed !
        for e in PreOrderIter(root):
            del e.childrens_to_parse


        return self.preprocessing_tree(root)

    def nextLevel(self, text_to_parse):
        '''
        :return: list of nextChild e.g., ['a', {'XOR':'a,b'}, 'b']
        if match is a dict, then it is an operator (e.g., {'XOR':'a,b,AND(d,e)'}
        else it is a leaf (e.g., a)
        afterMatch is the string after the first child
        '''

        list_to_return = []
        rest = text_to_parse
        while True:
            block, rest = self.nextChild(rest)
            list_to_return.append(block)

            if len(rest)==0:
                break


        return list_to_return

    def nextChild(self, text_to_parse):
        '''
        Given a text_to_parse, this function returns the next node (activity or operator)
        :return: (match, afterMatch)
        if match the match is a tuple, then it is an operator (e.g., ('XOR','a,b,AND(d,e)')}
        else it is a leaf (e.g., a)
        afterMatch is the string after the first child
        '''

        # First step: match first comma or opening bracket (
        groups = re.match(r'(.*?)($|,|\()(.*)', text_to_parse)

        if groups:
            firstMatch = groups.group(2)
            beforeMatch = groups.group(1)
            afterMatch = groups.group(3)

            if (firstMatch == ','):
                return (beforeMatch, afterMatch)


            # Given the input...
            # Xor( Xor(2,3),Xor(4,5) , 3), 5
            # we would like to add "Xor( Xor(2,3),Xor(4,5)) , 3" to array_to_return and recursively parse for ", 5"
            else:
                afterMatchBlock = ""
                counter_bracket = 0
                for char in afterMatch:
                    if (char == '('):
                        counter_bracket += 1
                    elif (char == ')'):
                        counter_bracket -= 1

                    if counter_bracket == -1:
                        break

                    afterMatchBlock += char

                # We remove last parenthesis
                afterBlock = text_to_parse[len(beforeMatch+'('+afterMatchBlock):].replace(')','',1)
                return ((beforeMatch, afterMatchBlock), afterBlock)
                #array_to_return.append({firstMatch: afterMatch})
        else:
            return (None, "")

    def preprocessing_tree(self, tree):
        def add_type_of_node():
            # Add the type of nodes as attribute
            for e in PreOrderIter(tree):
                if e.name in ['XorLoop', 'Seq', 'Xor', 'tau', 'And']:
                    e.type = e.name
                else:
                    e.type = 'task'

        def give_short_name():
            # todo: it might be that a name is used in logs but not in process_tree (add it !)
            for i, e in enumerate(PreOrderIter(tree)):
                if e.type == 'task':
                    e.shortname = e.name
                else:
                    e.shortname = '['+e.type+str(i)+']'

        add_type_of_node()

        give_short_name()
        return tree


