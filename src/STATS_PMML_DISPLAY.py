#/***********************************************************************
# * Licensed Materials - Property of IBM 
# *
# * IBM SPSS Products: Statistics Common
# *
# * (C) Copyright IBM Corp. 2014
# *
# * US Government Users Restricted Rights - Use, duplication or disclosure
# * restricted by GSA ADP Schedule Contract with IBM Corp. 
# ************************************************************************/

"""STATS PMML DISPLAY extension command"""

__author__ =  'JKP'
__version__=  '1.0.1'

# history
# 16-may-2012 original version


helptext = """STATS PMML DISPLAY FILES="file-expression"
[/HELP].

This command displays summary model information in PMML files.
It requires at least Statistics version 20.

file-expression can be the name of an (xml) PMML file or a wildcard expression.
Statistics file handles are supported.

Examples:
STATS PMML DISPLAY FILES="c:/mymodels/regression.xml".

STATS PMML DISPLAY FILES="c:/mymodels/*.xml".

If a selected file is not a PMML file or from DISCRIMINANT, it is skipped
with a message.

If /HELP is used, this help is displayed and nothing else is done.
"""

import spss
from extension import Template, Syntax, processcmd
from spssaux import FileHandles
import glob, os, os.path, re, time, textwrap, sys
from xml.etree import ElementTree



# display functions - the parameter for each is the model element
class Printer(object):
    """main printing class"""
    def __init__(self, tree, text):
        self.tree = tree
        self.text = text
    
    def printHeader(self):
        self.text.addtext("Model: %s" % re.sub(r"{.*}", "", self.tree.tag))
        for k,v in self.tree.attrib.items():
            self.text.addtext("%s: %s" % (k, v))
        self.text.addtext( _("""Details"""))

class GeneralRegressionModel(Printer):
    """Regression models of all types"""
    def __init__(self, tree, text):
        super(GeneralRegressionModel, self).__init__(tree, text)
        self.printHeader()
        modeltype = self.tree.attrib['modelType']
        if modeltype in ['regression']:
            parmelts = self.tree.iterfind(ns+"ParamMatrix/" + ns + "PCell")
            for p in parmelts:
                self.text.addtext("""%s: %s""" % (p.attrib['parameterName'], p.attrib['beta']))
        elif modeltype in ['multinomialLogistic', 'CoxRegression', 'generalizedLinear', 'generalLinear']:
            plist = {}
            for p in self.tree.iterfind(".//" + ns + 'EventValues/' + ns + 'Value'):
                self.text.addtext( _("""Event Value: %s Property: %s""") % (p.attrib['value'], p.attrib['property']))
            plistelts = self.tree.iterfind(ns+'ParameterList/' + ns + 'Parameter')
            for p in plistelts:
                plist[p.attrib['name']] = p.attrib['label']
            parmelts = self.tree.iterfind(ns+'ParamMatrix/'+ns+'PCell')
            for p in parmelts:
                if 'targetCategory' in p.attrib:
                    targetitem = _("""Target Category: %s""") % p.attrib['targetCategory']
                else:
                    targetitem  = ""
                if 'df' in p.attrib:
                    dfitem = _("""df: %s""") % p.attrib['df']
                else:
                    dfitem = ""
                self.text.addtext(_("""%s Parameter: %s beta: %.5f %s""") % \
                    (targetitem,\
                    plist.get(p.attrib['parameterName'], p.attrib['parameterName']),\
                    float(p.attrib['beta']),\
                    dfitem))
            
        
    
class TreeModel(Printer):
    @staticmethod
    def parChildIterator(elt):
        """Iterate over nodes while preserving parent information
        
        elt should have tag "Node", and only child nodes of that type are
        included"""
        
        nodetag = ns + 'Node'
        stack = []
        while True:
            for c in reversed([el for el in elt if el.tag == nodetag]):
                stack.append((c, elt))
            if not stack:
                return
            elt, parent = stack.pop()
            yield parent, elt
            
    def __init__(self, tree, text):
        super(TreeModel, self).__init__(tree, text)
        self.printHeader()
        rootnode = self.tree.find(".//" + ns + "Node")
        self.text.addtext(_("""Root Node: %s""") % rootnode.attrib['id'])
        for par, child in TreeModel.parChildIterator(rootnode):
            self.text.addtext(_("""Node: %s Parent Node: %s""") % (child.attrib['id'], par.attrib['id']))
            cond = []
            for pp in child.iterfind("./" + ns + 'CompoundPredicate'):
                op1 = pp.attrib['booleanOperator']
                qqq = pp.find("./" + ns + 'CompoundPredicate')
                op2 = qqq.attrib['booleanOperator']
                for ppp in qqq.iterfind("./" + ns +  'SimplePredicate'):
                    if len(cond) > 0:
                        cond.append(op2)
                    cond.append(ppp.attrib['field'] + " " + ppp.attrib['operator'] + " " + ppp.attrib['value'])
                self.text.addtext(_("""     Definition: %s""") % " ".join(cond))
        
        
class ClusteringModel(Printer):
    def __init__(self, tree, text):
        super(ClusteringModel, self).__init__(tree, text)
        self.printHeader()
        parmelts = self.tree.iterfind('.//' + ns + 'ComparisonMeasure')
        for p in parmelts:
            if 'kind' in p.attrib:
                self.text.addtext(_("""Comparison Measure: %s""") % p.attrib['kind'])
            eparms = p.find('.//' + ns + 'Extension')
            if eparms is not None and 'value' in eparms.attrib:
                self.text.addtext(_("""     Value: %s""") % eparms.attrib['value'])
        parmelts = self.tree.iterfind('.//' + ns + 'ClusteringField')
        for p in parmelts:
            self.text.addtext(_("""Clustering Field: %s""") % p.attrib['field'])
        

class RuleSetModel(Printer):
    def __init__(self, tree, text):
        super(RuleSetModel, self).__init__(tree, text)
        self.printHeader()
        rules = self.tree.find(".//" + ns + 'RuleSet')
        ruleselection = rules.find("./" + ns + 'RuleSelectionMethod')
        if ruleselection is not None:
            self.text.addtext(_("""Rule Selection Method"""))
            for k, v in ruleselection.attrib.items():
                self.text.addtext("%s: %s" % ( k, v))
        for rule in rules.iter():
            if rule.tag.endswith("SimpleRule"):
                ruleid = rule.attrib['id']
                item = rule.find("./" + ns + 'CompoundPredicate')
                if item is not None:
                    conj = item.attrib['booleanOperator']
                    simple = []
                    for srule in item.iterfind(".//" + ns + 'SimplePredicate'):
                        simple.append(" ".join([srule.attrib['field'], srule.attrib['operator'], srule.attrib['value']]))
                    self.text.addtext(_("""id: %s %s""") % (ruleid, (" " + conj + " ").join(simple)))
                else:
                    item = rule.find("./" + ns + 'SimplePredicate')
                    if item is not None:
                        self.text.addtext(_("""id: %s %s""") % (ruleid, " ".join([item.attrib['field'], item.attrib['operator'], item.attrib['value']])))
                    
            

class discriminantmodel(Printer):
    def __init__(self, tree, text):
        super(discriminantmodel, self).__init__(tree, text)
        self.printHeader()

        for funccoefs in tree.iterfind(".//" + ns + 'function-coefficients'):
            self.text.addtext(_("""Coefficients"""))
            for cell in funccoefs.iterfind("./" + ns + 'cell'):
                if 'row' in cell.attrib:
                    item = _("""Row: %s """) % cell.attrib['row']
                else:
                    item = ""
                self.text.addtext(_("""%sColumn: %s Value: %.5f""") % (item, cell.attrib['column'], float(cell.attrib['value'])))
        prior = tree.iterfind(".//" + ns + 'prior-value')
        if prior is not None:
            self.text.addtext(_("""Priors"""))
        for p in prior:
            self.text.addtext(_("""Target Category: %s Prior Value: %s""") % (p.attrib['target-category'], p.attrib['value']))

class NeuralNetwork(Printer):
    def __init__(self, tree, text):
        super(NeuralNetwork, self).__init__(tree, text)
        self.printHeader()
        for item in self.tree.iterfind(".//" + ns + "NeuralLayer"):
            for k,v in item.attrib.items():
                self.text.addtext("%s: %s" % (k,  v))
        

    

# define printing class for each model type
modelprints = set(["TreeModel", "GeneralRegressionModel", "ClusteringModel", "RuleSetModel",
    "discriminant-model", "NeuralNetwork"])
prints = {}
for m in modelprints:
    prints[m] = locals()[m.replace("-","")]

def dopmml(files):
    """Display pmml files"""
    
    # debugging
    #makes debug apply only to the current thread
    # The global namespace qualifier depends on the PMML and is set per file
    global ns
    #try:
        #import wingdbstub
        #if wingdbstub.debugger != None:
            #import time
            #wingdbstub.debugger.StopDebug()
            #time.sleep(2)
            #wingdbstub.debugger.StartDebug()
        #import thread
        #wingdbstub.debugger.SetDebugThreads({thread.get_ident(): 1}, default_policy=0)
        ## for V19 use
        #SpssClient._heartBeat(False)
    #except:
        #pass
    fh = FileHandles()
    files = fh.resolve(files)   # note that files might be a wildcard file expression
    spss.StartProcedure("STATS PMML DISPLAY", "STATSPMMLINFO")
    didone = False
    try:
        for fnumber, f in enumerate(glob.glob(files)):
            text = Text("""STATS_PMML_DISPLAY-""" + str(fnumber) )
            didone = True
            try:
                try:
                    tree = ElementTree.parse(f)
                    root = tree.getroot()
                    first = True
                except:
                    raise ValueError(_("""Invalid xml.  Error: %s File: %s""") % (sys.exc_info()[1].message, f))
                # Discriminant xml is not tagged as pmml
                if not (root.tag.endswith("PMML") or root.tag.endswith("spss-ml")):
                    text.addtext("""%f is not a PMML file""" % f)
                    continue
      
                ftime = time.ctime(os.stat(f).st_mtime)
                text.title = _("""Summary Information: %s""") % f
                text.addtext( _("""Summary Model Information for File: %s\nmodified: %s\n""") % (f, ftime))
                for ch in root.getchildren():
                    if first:
                        first = False
                        # find the namespace - there ought to be a better way :-)
                        thetag = re.match(r"\{.*\}", ch.tag)
                        if thetag:
                            ns = thetag.group()
                        else:
                            ns = ""                    
                    chtag = re.sub(r"""\{.*\}""", "", ch.tag)
                    if chtag == "Header":
                        doHeader(chtag, ch)
                    elif chtag == "TransformationDictionary":
                        displayTransformations(ch, text)
                    elif chtag == "MiningModel":
                        displayMining(ch, text)
                    elif chtag in ['DataDictionary', 'Extension', 'dictionary']:
                        continue
                    elif chtag == "model" and ch.find("./" + ns + 'discriminant-model') is not None:
                        disc = ch.find("./" + ns + 'discriminant-model')
                        prints['discriminant-model'](disc, text)
                    elif chtag not in prints:
                        text.addtext( _("""Cannot display element: %s""") % chtag)
                    else:                
                        prints[chtag](ch, text)
            finally:
                text.printit()
                del(text)   # should not be necessary
    finally:
        spss.EndProcedure()
    if not didone:
        raise ValueError( _("""No files were found to process.  File Specification: %s""") % files)

def doHeader(chtag, ch):
    ccc = ch.getchildren()
    for cccc in ccc:
        if cccc.tag.endswith("Application"):
            d = cccc.attrib
            print _("""Application: %s, Version: %s""") % (d["name"], d["version"])
            break

def displayTransformations(ch, text):
    text.addtext(_("""***** Transformations"""))
    for ccc in ch.iterfind(ns+'DerivedField'):
        if 'name' in ccc.attrib:
            text.addtext( _("""Output Field: %s""") % ccc.attrib['name'])
        for cccc in ccc.iterfind(".//" + ns + 'FieldRef'):
            text.addtext( _("""     Input Field: %s""") % cccc.attrib['field'])
        for cccc in ccc.iterfind(".//" + ns + 'NormContinuous'):
            text.addtext( _("""     Input Field: %s""") % cccc.attrib['field'])
        for cccc in ccc.iterfind(".//" + ns + 'Discretize'):
            if 'field' in cccc.attrib:
                text.addtext(_("""Input Field: %s""") % cccc.attrib['field'])
        for cccc in ccc.iterfind(".//" + ns + 'NormDiscrete'):
            field = cccc.attrib.get("field", cccc.attrib.get('name'))
            if 'value' in cccc.attrib:
                valuestring = _("""Value: %s""") % cccc.attrib['value']
            else:
                valuestring = ""
            text.addtext( _("""     Input Field: %s, %s""") % (field, valuestring))
            
def displayMining(ch, text):
    text.addtext(_("***** Mining Model"""))
    for k, v in ch.attrib.items():
        text.addtext("""%s : %s""" % (k, v))
    for segment in ch.iterfind(".//" + ns + "Segment"):
        text.addtext(_("""Segment"""))
        text.addtext(" ".join(["""%s : %s""" % (k,v) for k, v in segment.attrib.items()]))
        for item in segment.iterfind("./"):
            itemtag = re.sub(r"""\{.*\}""", "", item.tag)
            if itemtag in prints:
                prints[itemtag](item, text)
            
            
class Text(object):
    """Create and manage Viewer text block"""
    def __init__(self, outlinename, title=""):
        self.outlinename = outlinename
        self.title = title
        self.text = []
        self.wrapper = textwrap.TextWrapper(subsequent_indent="     ", width=90)
        self.printed = False
    
    def addtext(self, line):
        """Add a line of text
        
        text is the text to add without a trailing linefeed
        
        text is wrapped to a 90 character line length"""
        self.text.extend(self.wrapper.wrap(line))
        
    def printit(self):
        """Print accumulated text"""
        
        if self.printed:
            return
        self.printed = True
        spss.TextBlock(self.outlinename, "\n".join(self.text), self.title)

def Run(args):
    """Execute the STATS PMML DISPLAY extension command"""

    args = args[args.keys()[0]]

    oobj = Syntax([
        Template("FILES", subc="",  ktype="literal", var="files", islist=False),
        Template("HELP", subc="", ktype="bool")])

    
    #enable localization
    global _
    try:
        _("---")
    except:
        def _(msg):
            return msg
    # A HELP subcommand overrides all else
    if args.has_key("HELP"):
        #print helptext
        helper()
    else:
        processcmd(oobj, args, dopmml)

def helper():
    """open html help in default browser window
    
    The location is computed from the current module name"""
    
    import webbrowser, os.path
    
    path = os.path.splitext(__file__)[0]
    helpspec = "file://" + path + os.path.sep + \
         "markdown.html"
    
    # webbrowser.open seems not to work well
    browser = webbrowser.get()
    if not browser.open_new(helpspec):
        print("Help file not found:" + helpspec)
try:    #override
    from extension import helper
except:
    pass