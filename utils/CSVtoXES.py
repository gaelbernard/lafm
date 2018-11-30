class CSVtoXES:
    '''
    Transform a log (e.g., ['1-3-1','1-1'])
    in a xes file (xml file describing event logs).
    '''
    def __init__(self, xes_path, log):
        self.xes_path = xes_path
        self.log = log

    def write_xes(self):
        with open(self.xes_path, 'w') as myfile:
            myfile.write(self.prepare_str())

    def prepare_str(self):
        xes = self.get_head()
        for trace_id, seq in enumerate(self.log.SequenceTxt):
            seq = seq.split("-")
            xes+='	<trace>\n'
            xes+='      <string key="concept:name" value="'+str(trace_id)+'"/>\n'
            for activity in seq:
                xes+='      <event>\n'
                xes+='          <string key="concept:name" value="'+activity+'"/>\n'
                xes+='      </event>\n'
            xes+='	</trace>\n'
        xes+='</log>\n'

        return xes

    def get_head(self):
        return '''<?xml version="1.0" encoding="UTF-8"?>
    <log>
        <extension name="Concept" prefix="concept" uri="http://www.xes-standard.org/concept.xesext"/>
        <extension name="Lifecycle" prefix="lifecycle" uri="http://www.xes-standard.org/lifecycle.xesext"/>
    '''



